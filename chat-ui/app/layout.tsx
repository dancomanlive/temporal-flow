import './globals.css'

export const metadata = {
  title: 'Temporal Flow Chat UI',
  description: 'Chat interface for Temporal workflow engine',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
