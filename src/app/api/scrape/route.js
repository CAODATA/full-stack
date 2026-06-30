import { google } from 'googleapis';
import * as xlsx from 'xlsx';
import { NextResponse } from 'next/server';

const API_KEY = "AIzaSyCFE_4B4q8zJZR1L502_RrtdHbuj187s7w";

function extractVideoId(url) {
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i);
  return match ? match[1] : null;
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

    const date = new Date(c.published_at);
    const formattedDate = date.toISOString().replace('T', ' ').substring(0, 19);

    cleaned.push({
      'Phân loại': c.type === 'reply' ? 'Phản hồi' : 'Bình luận gốc',
      'Phản hồi ai': cleanParent,
      'Tác giả': cleanAuthor,
      'Nội dung bình luận': cleanText,
      'Lượt thích': c.likes,
      'Ngày đăng (UTC)': formattedDate
    });
  }
  return cleaned;
}

export async function POST(req) {
  try {
    const body = await req.json();
    const { links } = body;

    if (!links || links.length === 0) {
      return NextResponse.json({ error: 'No links provided' }, { status: 400 });
    }

    const urls = Array.isArray(links) ? links : links.split('\n').map(l => l.trim()).filter(l => l);
    const youtube = google.youtube({ version: 'v3', auth: API_KEY });

    const wb = xlsx.utils.book_new();
    const allData = [];

    for (const url of urls) {
      const vid = extractVideoId(url);
      if (!vid) continue;

      allData.push(['--- LINK YOUTUBE ---', `https://youtu.be/${vid}`, '', '', '', '']);

      const rawComments = await getComments(youtube, vid, 100000);
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

    const ws = xlsx.utils.aoa_to_sheet(allData);

    // Auto fit columns width somewhat
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
