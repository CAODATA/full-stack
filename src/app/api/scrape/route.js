import { google } from 'googleapis';
import * as xlsx from 'xlsx';
import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';

const API_KEY = "AIzaSyCFE_4B4q8zJZR1L502_RrtdHbuj187s7w";

function extractVideoId(url) {
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i);
  return match ? match[1] : null;
}

function getLinkType(url) {
  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    return 'youtube';
  }
  if (url.includes('facebook.com') || url.includes('fb.watch') || url.includes('fb.com')) {
    return 'facebook';
  }
  return 'unknown';
}

async function getComments(youtube, videoId, maxResults = 100000) {
  let allComments = [];
  let nextPageToken = null;
  let count = 0;

  try {
    while (count < maxResults) {
      const response = await youtube.commentThreads.list({
        part: ['snippet', 'replies'],
        videoId: videoId,
        maxResults: 100,
        pageToken: nextPageToken,
        textFormat: 'plainText'
      });

      const items = response.data.items || [];
      for (const item of items) {
        const top = item.snippet.topLevelComment.snippet;
        allComments.push({
          video_id: videoId,
          type: 'comment',
          author: top.authorDisplayName,
          text: top.textOriginal,
          likes: top.likeCount,
          published_at: top.publishedAt,
          parent_author: null
        });
        count++;

        if (item.replies && item.replies.comments) {
          for (const rItem of item.replies.comments) {
            const reply = rItem.snippet;
            allComments.push({
              video_id: videoId,
              type: 'reply',
              author: reply.authorDisplayName,
              text: reply.textOriginal,
              likes: reply.likeCount,
              published_at: reply.publishedAt,
              parent_author: top.authorDisplayName
            });
          }
        }
      }

      nextPageToken = response.data.nextPageToken;
      if (!nextPageToken || count >= maxResults) break;
    }
  } catch (error) {
    console.error(`Error scraping ${videoId}:`, error.message);
  }
  return allComments;
}

function runPythonScraper(config) {
  return new Promise((resolve, reject) => {
    const tempDir = path.join(os.tmpdir(), 'yt-scraper-web-tmp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    const configId = Date.now();
    const configPath = path.join(tempDir, `fb_config_${configId}.json`);
    const outputPath = path.join(tempDir, `fb_output_${configId}.json`);
    
    config.output_file = outputPath;
    
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf-8');
    
    const pythonScriptPath = path.join(process.cwd(), 'scripts', 'crawlfb_comments.py');
    const command = `python "${pythonScriptPath}" "${configPath}"`;
    
    console.log(`Running Python script: ${command}`);
    
    exec(command, (error, stdout, stderr) => {
      // Clean up config file
      try { fs.unlinkSync(configPath); } catch (_) {}
      
      if (error) {
        console.error(`Python script error:`, error);
        console.error(`stderr:`, stderr);
        // Clean up output file if it was created
        try { fs.unlinkSync(outputPath); } catch (_) {}
        reject(new Error(stderr || error.message || 'Lỗi không xác định khi cào Facebook'));
        return;
      }
      
      console.log(`Python stdout:`, stdout);
      
      try {
        if (!fs.existsSync(outputPath)) {
          resolve([]);
          return;
        }
        const rawData = fs.readFileSync(outputPath, 'utf-8');
        const comments = JSON.parse(rawData);
        // Clean up output file
        try { fs.unlinkSync(outputPath); } catch (_) {}
        resolve(comments);
      } catch (err) {
        console.error('Error reading Python scraper output:', err);
        reject(err);
      }
    });
  });
}

function cleanData(comments) {
  const cleaned = [];
  const seen = new Set();

  for (const c of comments) {
    if (!c.text || !c.author) continue;

    const cleanText = c.text.replace(/[\n\r]+/g, ' ').trim();
    let cleanAuthor = c.author;
    if (cleanAuthor.startsWith('@')) cleanAuthor = cleanAuthor.substring(1);

    let cleanParent = c.parent_author || '';
    if (cleanParent.startsWith('@')) cleanParent = cleanParent.substring(1);

    const uniqueKey = `${c.video_id}|${cleanAuthor}|${cleanText}`;
    if (seen.has(uniqueKey)) continue;
    seen.add(uniqueKey);

    let formattedDate = c.published_at;
    try {
      const date = new Date(c.published_at);
      if (!isNaN(date.getTime())) {
        formattedDate = date.toISOString().replace('T', ' ').substring(0, 19);
      }
    } catch (_) {}

    cleaned.push({
      'Phân loại': c.type === 'reply' ? 'Phản hồi' : 'Bình luận gốc',
      'Phản hồi ai': cleanParent,
      'Tác giả': cleanAuthor,
      'Nội dung bình luận': cleanText,
      'Lượt thích': c.likes,
      'Ngày đăng (UTC)': formattedDate,
      video_id: c.video_id
    });
  }
  return cleaned;
}

export async function POST(req) {
  try {
    const body = await req.json();
    const { links, chromeUserData, chromeProfile, maxComments, fbEmail, fbPassword } = body;

    if (!links || links.length === 0) {
      return NextResponse.json({ error: 'No links provided' }, { status: 400 });
    }

    const urls = Array.isArray(links) ? links : links.split('\n').map(l => l.trim()).filter(l => l);
    
    // Group links by type
    const youtubeUrls = [];
    const facebookUrls = [];
    
    for (const url of urls) {
      const type = getLinkType(url);
      if (type === 'youtube') {
        youtubeUrls.push(url);
      } else if (type === 'facebook') {
        facebookUrls.push(url);
      }
    }

    const allData = [];
    
    // 1. Process YouTube links if any
    if (youtubeUrls.length > 0) {
      const youtube = google.youtube({ version: 'v3', auth: API_KEY });
      const limit = maxComments ? parseInt(maxComments) : 100000;
      
      for (const url of youtubeUrls) {
        const vid = extractVideoId(url);
        if (!vid) continue;

        allData.push(['--- LINK YOUTUBE ---', `https://youtu.be/${vid}`, '', '', '', '']);

        const rawComments = await getComments(youtube, vid, limit);
        const cleaned = cleanData(rawComments);

        if (cleaned.length === 0) {
          allData.push(['Không có comments nào.', '', '', '', '', '']);
        } else {
          allData.push(['Phân loại', 'Phản hồi ai', 'Tác giả', 'Nội dung bình luận', 'Lượt thích', 'Ngày đăng (UTC)']);
          for (const row of cleaned) {
            allData.push([
              row['Phân loại'], 
              row['Phản hồi ai'], 
              row['Tác giả'], 
              row['Nội dung bình luận'], 
              row['Lượt thích'], 
              row['Ngày đăng (UTC)']
            ]);
          }
        }
        allData.push(['', '', '', '', '', '']);
        allData.push(['', '', '', '', '', '']);
      }
    }

    // 2. Process Facebook links if any
    if (facebookUrls.length > 0) {
      // Resolve Chrome user data directory path
      // Prefer UI setting, then hardcoded user path C:\Users\3551\..., then general LocalAppData
      let finalUserData = chromeUserData || '';
      if (!finalUserData) {
        const defaultLocal = process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'Google\\Chrome\\User Data') : '';
        const hardcoded3551 = 'C:\\Users\\3551\\AppData\\Local\\Google\\Chrome\\User Data';
        const hardcodedAdmin = 'C:\\Users\\Admin\\AppData\\Local\\Google\\Chrome\\User Data';
        
        if (defaultLocal && fs.existsSync(defaultLocal)) {
          finalUserData = defaultLocal;
        } else if (fs.existsSync(hardcoded3551)) {
          finalUserData = hardcoded3551;
        } else if (fs.existsSync(hardcodedAdmin)) {
          finalUserData = hardcodedAdmin;
        }
      }

      const fbConfig = {
        urls: facebookUrls,
        chrome_user_data: finalUserData,
        chrome_profile: chromeProfile || 'Default',
        max_comments: maxComments ? parseInt(maxComments) : 100000,
        fb_email: fbEmail || process.env.FB_EMAIL || '',
        fb_password: fbPassword || process.env.FB_PASSWORD || ''
      };

      try {
        const rawFbComments = await runPythonScraper(fbConfig);
        const cleanedFb = cleanData(rawFbComments);
        
        // Group Facebook comments back by post URL to structure the sheet
        for (const url of facebookUrls) {
          allData.push(['--- LINK FACEBOOK ---', url, '', '', '', '']);
          
          const postComments = cleanedFb.filter(item => item.video_id === url);
          
          if (postComments.length === 0) {
            allData.push(['Không có bình luận nào.', '', '', '', '', '']);
          } else {
            allData.push(['Phân loại', 'Phản hồi ai', 'Tác giả', 'Nội dung bình luận', 'Lượt thích', 'Ngày đăng (UTC)']);
            for (const row of postComments) {
              allData.push([
                row['Phân loại'], 
                row['Phản hồi ai'], 
                row['Tác giả'], 
                row['Nội dung bình luận'], 
                row['Lượt thích'], 
                row['Ngày đăng (UTC)']
              ]);
            }
          }
          allData.push(['', '', '', '', '', '']);
          allData.push(['', '', '', '', '', '']);
        }
      } catch (fbError) {
        console.error('Facebook scraping failed:', fbError);
        return NextResponse.json({ error: `Lỗi cào Facebook: ${fbError.message}` }, { status: 500 });
      }
    }

    if (allData.length === 0) {
      return NextResponse.json({ error: 'Không có liên kết hợp lệ nào được tìm thấy.' }, { status: 400 });
    }

    const wb = xlsx.utils.book_new();
    const ws = xlsx.utils.aoa_to_sheet(allData);

    ws['!cols'] = [
      { wch: 15 }, // Phân loại
      { wch: 25 }, // Phản hồi ai
      { wch: 25 }, // Tác giả
      { wch: 100 }, // Nội dung
      { wch: 10 }, // Likes
      { wch: 20 }, // Ngày đăng
    ];

    xlsx.utils.book_append_sheet(wb, ws, 'Comments');

    const buf = xlsx.write(wb, { type: 'buffer', bookType: 'xlsx' });

    return new NextResponse(buf, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': 'attachment; filename="tat_ca_comments_clean.xlsx"'
      }
    });

  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
