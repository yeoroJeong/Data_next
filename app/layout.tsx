import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DATA NEXT | SSAFY 데이터 채용',
  description: 'SSAFY 데이터반을 위한 데이터·AI·SW 신입 채용 공고 모음',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body>{children}</body></html>;
}
