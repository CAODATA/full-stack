import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  const filePath = path.join(process.cwd(), 'public', 'login_error.png');
  if (!fs.existsSync(filePath)) {
    return new NextResponse('No error screenshot found. Perform a scrape attempt first.', { status: 404 });
  }

  const imageBuffer = fs.readFileSync(filePath);
  return new NextResponse(imageBuffer, {
    headers: {
      'Content-Type': 'image/png',
      'Cache-Control': 'no-store, max-age=0, must-revalidate',
    },
  });
}
