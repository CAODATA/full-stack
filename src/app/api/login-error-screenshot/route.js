import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get('type');
  const filename = type === 'verification' ? 'verification_error.png' : 'login_error.png';
  
  const filePath = path.join(process.cwd(), 'public', filename);
  if (!fs.existsSync(filePath)) {
    return new NextResponse(`No error screenshot found for ${filename}. Perform a scrape attempt first.`, { status: 404 });
  }

  const imageBuffer = fs.readFileSync(filePath);
  return new NextResponse(imageBuffer, {
    headers: {
      'Content-Type': 'image/png',
      'Cache-Control': 'no-store, max-age=0, must-revalidate',
    },
  });
}
