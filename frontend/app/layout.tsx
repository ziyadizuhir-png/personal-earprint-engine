import "./globals.css";

export const metadata = {
  title: "Personal Earprint Engine",
  description: "Personal IEM earprint engine",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
