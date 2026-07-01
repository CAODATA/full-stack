import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  const filePath = path.join(process.cwd(), 'public', 'login_error.html');
  if (!fs.existsSync(filePath)) {
    return new NextResponse('No error HTML found. Perform a scrape attempt first.', { status: 404 });
  }

  const htmlContent = fs.readFileSync(filePath, 'utf-8');
  return new NextResponse(htmlContent, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store, max-age=0, must-revalidate',
    },
  });
}
