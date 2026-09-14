import { useCallback, useEffect, useRef, useState } from 'react'

/** Web Speech API hook: mic input (SpeechRecognition) + read-aloud (speechSynthesis).
 * Both features degrade gracefully — `supported` flags let the UI hide buttons. */

type SR = {
  new (): SRInstance
}
interface SRInstance {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
  start: () => void
  stop: () => void
}

export function useSpeech(lang = 'en-IN') {
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [transcript, setTranscript] = useState('')
  const recRef = useRef<SRInstance | null>(null)

  const srSupported =
    typeof window !== 'undefined' &&
    ((window as unknown as { SpeechRecognition?: SR }).SpeechRecognition !== undefined ||
      (window as unknown as { webkitSpeechRecognition?: SR }).webkitSpeechRecognition !== undefined)
  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

  const startListening = useCallback(() => {
    if (!srSupported) return
    const W = window as unknown as { SpeechRecognition?: SR; webkitSpeechRecognition?: SR }
    const Ctor = W.SpeechRecognition ?? W.webkitSpeechRecognition
    if (!Ctor) return
    const rec = new Ctor()
    recRef.current = rec
    rec.lang = lang
    rec.continuous = false
    rec.interimResults = false
    rec.onresult = (e) => {
      const t = e.results?.[0]?.[0]?.transcript ?? ''
      setTranscript(t)
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    setTranscript('')
    setListening(true)
    try {
      rec.start()
    } catch {
      setListening(false)
    }
  }, [lang, srSupported])

  const stopListening = useCallback(() => {
    recRef.current?.stop()
    setListening(false)
  }, [])

  const speak = useCallback(
    (text: string) => {
      if (!ttsSupported || !text) return
      window.speechSynthesis.cancel()
      const u = new SpeechSynthesisUtterance(text.slice(0, 1200))
      u.lang = lang
      u.rate = 1.02
      u.onend = () => setSpeaking(false)
      u.onerror = () => setSpeaking(false)
      setSpeaking(true)
      window.speechSynthesis.speak(u)
    },
    [lang, ttsSupported],
  )

  const stopSpeaking = useCallback(() => {
    if (ttsSupported) window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [ttsSupported])

  useEffect(() => () => {
    recRef.current?.stop()
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel()
  }, [])

  return {
    srSupported,
    ttsSupported,
    listening,
    transcript,
    startListening,
    stopListening,
    speaking,
    speak,
    stopSpeaking,
  }
}
