import { useRef, useState } from 'react'
import { ImageUp } from 'lucide-react'
import { api } from '../api'

export function ImageAnalyzer() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  const handle = async (file: File) => {
    setBusy(true)
    setErr(null)
    setResult(null)
    const b64 = await new Promise<string>((resolve, reject) => {
      const r = new FileReader()
      r.onload = () => resolve((r.result as string).split(',')[1] ?? '')
      r.onerror = reject
      r.readAsDataURL(file)
    })
    setPreview(`data:${file.type};base64,${b64}`)
    try {
      const res = await api.analyzeImage(b64, file.type || 'image/png')
      setResult(res.text)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'analysis failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="card-title"><ImageUp size={15} /> Image analysis — charts & screenshots</div>
      <p className="faint" style={{ marginTop: -6, marginBottom: 12 }}>
        Upload a price chart or a social-media “tip” screenshot: the AI explains what it shows and what a
        beginner should be skeptical about. It never validates trading advice.
      </p>
      <input
        ref={fileRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        hidden
        onChange={(e) => e.target.files?.[0] && handle(e.target.files[0])}
      />
      <button className="btn" onClick={() => fileRef.current?.click()} disabled={busy}>
        {busy ? 'analyzing…' : 'Choose image'}
      </button>
      {preview ? (
        <img src={preview} alt="uploaded" style={{ marginTop: 12, maxWidth: '100%', borderRadius: 12, border: '1px solid var(--card-border)' }} />
      ) : null}
      {err ? <div className="err-box" style={{ marginTop: 12 }}>{err}</div> : null}
      {result ? (
        <div style={{ marginTop: 12, fontSize: 13.5, whiteSpace: 'pre-wrap', lineHeight: 1.65 }}>{result}</div>
      ) : null}
    </div>
  )
}
