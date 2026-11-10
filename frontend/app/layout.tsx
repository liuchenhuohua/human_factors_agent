import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "人因工程个人助手",
  description: "把人因痛点转化为可追溯的研究与建议",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

