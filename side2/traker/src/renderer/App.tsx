import React, { useEffect, useMemo, useRef, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { parseBlob } from "music-metadata-browser";
import { loadPdfFromFile, renderPageToCanvas } from "./pdf";

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

const readNumber = (key: string, fallback: number) => {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
};

const readBoolean = (key: string, fallback: boolean) => {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return raw === "true";
  } catch {
    return fallback;
  }
};

type Chapter = {
  title: string;
  start: number;
  end?: number;
};

export default function App() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [pdfName, setPdfName] = useState("");
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isRendering, setIsRendering] = useState(false);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [error, setError] = useState("");

  const [audioName, setAudioName] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(() =>
    readNumber("sync:playbackRate", 1)
  );
  const [isParsingChapters, setIsParsingChapters] = useState(false);
  const [chapters, setChapters] = useState<Chapter[]>([]);

  const [zoom, setZoom] = useState(() => readNumber("sync:zoom", 1.2));
  const [autoFlip, setAutoFlip] = useState(() =>
    readBoolean("sync:autoFlip", true)
  );
  const [pageOffset, setPageOffset] = useState(() =>
    readNumber("sync:pageOffset", 0)
  );
  const [syncSpeed, setSyncSpeed] = useState(() =>
    readNumber("sync:syncSpeed", 1)
  );
  useEffect(() => {
    localStorage.setItem("sync:zoom", zoom.toString());
  }, [zoom]);

  useEffect(() => {
    localStorage.setItem("sync:autoFlip", String(autoFlip));
  }, [autoFlip]);

  useEffect(() => {
    localStorage.setItem("sync:pageOffset", pageOffset.toString());
  }, [pageOffset]);

  useEffect(() => {
    localStorage.setItem("sync:syncSpeed", syncSpeed.toString());
  }, [syncSpeed]);

  useEffect(() => {
    localStorage.setItem("sync:playbackRate", playbackRate.toString());
    if (audioRef.current) {
      audioRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  useEffect(() => {
    let canceled = false;
    if (!pdfDoc || !canvasRef.current) {
      return;
    }
    setIsRendering(true);
    renderPageToCanvas(pdfDoc, currentPage, canvasRef.current, zoom)
      .catch((err) => {
        if (!canceled) {
          setError(
            err instanceof Error ? err.message : "Failed to render PDF page."
          );
        }
      })
      .finally(() => {
        if (!canceled) {
          setIsRendering(false);
        }
      });
    return () => {
      canceled = true;
    };
  }, [pdfDoc, currentPage, zoom]);

  useEffect(() => {
    if (!autoFlip || !pdfDoc || totalPages === 0 || !audioRef.current) {
      return;
    }
    const interval = window.setInterval(() => {
      const audio = audioRef.current;
      if (!audio || audio.paused || !audioDuration) {
        return;
      }
      const pageDuration = audioDuration / totalPages;
      const effectiveTime = (audio.currentTime + pageOffset) * syncSpeed;
      const nextPage = clamp(
        Math.floor(effectiveTime / pageDuration) + 1,
        1,
        totalPages
      );
      setCurrentPage((prev) => (prev === nextPage ? prev : nextPage));
    }, 250);
    return () => window.clearInterval(interval);
  }, [
    autoFlip,
    audioDuration,
    pageOffset,
    syncSpeed,
    pdfDoc,
    totalPages
  ]);

  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (!pdfDoc || totalPages === 0) return;
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA")
      ) {
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setCurrentPage((prev) => clamp(prev - 1, 1, totalPages));
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        setCurrentPage((prev) => clamp(prev + 1, 1, totalPages));
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pdfDoc, totalPages]);

  const estimatedPageSeconds = useMemo(() => {
    if (!audioDuration || totalPages === 0) return 0;
    return audioDuration / totalPages;
  }, [audioDuration, totalPages]);

  const handlePdfChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsLoadingPdf(true);
    setError("");
    try {
      const doc = await loadPdfFromFile(file);
      setPdfDoc(doc);
      setTotalPages(doc.numPages);
      setCurrentPage(1);
      setPdfName(file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load PDF.");
    } finally {
      setIsLoadingPdf(false);
    }
  };

  const handleAudioChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    const url = URL.createObjectURL(file);
    setAudioUrl(url);
    setAudioName(file.name);
    setChapters([]);
    setIsParsingChapters(true);
    setError("");
    const audio = audioRef.current;
    if (audio) {
      audio.src = url;
      audio.load();
    }
    try {
      const metadata = await parseBlob(file);
      const nextChapters: Chapter[] =
        metadata.common?.chapters?.map((chapter, index) => ({
          title: chapter.title?.trim() || `Chapter ${index + 1}`,
          start: chapter.startTime ?? 0,
          end: chapter.endTime ?? undefined
        })) ?? [];
      setChapters(nextChapters);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to read audio chapters."
      );
    } finally {
      setIsParsingChapters(false);
    }
  };

  const handleJumpPage = (value: number) => {
    if (!pdfDoc) return;
    const next = clamp(Math.round(value), 1, totalPages);
    setCurrentPage(next);
  };
  const formatTime = (timeSeconds: number) => {
    if (!Number.isFinite(timeSeconds)) return "--:--";
    const total = Math.max(0, Math.floor(timeSeconds));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  return (
    <div className="app">
      <header className="top-bar">
        <div className="title">Desktop Sync Reader</div>
        <div className="file-inputs">
          <label className="file-button">
            Load PDF
            <input type="file" accept="application/pdf" onChange={handlePdfChange} />
          </label>
          <label className="file-button">
            Load Audio
            <input type="file" accept="audio/*,.m4b" onChange={handleAudioChange} />
          </label>
        </div>
      </header>

      <section className="content">
        <aside className="sidebar">
          <div className="panel">
            <h3>Files</h3>
            <div className="meta">
              <span>PDF:</span>
              <span>{pdfName || "Not loaded"}</span>
            </div>
            <div className="meta">
              <span>Audio:</span>
              <span>{audioName || "Not loaded"}</span>
            </div>
          </div>

          <div className="panel">
            <h3>Audio</h3>
            <audio
              ref={audioRef}
              controls
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onLoadedMetadata={(event) =>
                setAudioDuration(event.currentTarget.duration || 0)
              }
            />
            <div className="meta">
              <span>Status:</span>
              <span>{isPlaying ? "Playing" : "Paused"}</span>
            </div>
            <div className="meta">
              <span>Duration:</span>
              <span>
                {audioDuration ? `${audioDuration.toFixed(1)}s` : "--"}
              </span>
            </div>
            <label className="field">
              Playback speed
              <input
                type="number"
                min={0.1}
                step={0.1}
                value={playbackRate}
                onChange={(event) =>
                  setPlaybackRate(Math.max(0.1, Number(event.target.value)))
                }
              />
            </label>
            {isParsingChapters && (
              <div className="meta">
                <span>Chapters:</span>
                <span>Reading…</span>
              </div>
            )}
          </div>

          <div className="panel">
            <h3>Page</h3>
            <div className="page-row">
              <button
                type="button"
                onClick={() => handleJumpPage(currentPage - 1)}
                disabled={!pdfDoc || currentPage <= 1}
              >
                Prev
              </button>
              <span>
                {currentPage} / {totalPages || "--"}
              </span>
              <button
                type="button"
                onClick={() => handleJumpPage(currentPage + 1)}
                disabled={!pdfDoc || currentPage >= totalPages}
              >
                Next
              </button>
            </div>
            <label className="field">
              Jump to page
              <input
                type="number"
                min={1}
                max={totalPages || 1}
                value={currentPage}
                onChange={(event) =>
                  handleJumpPage(Number(event.target.value))
                }
                disabled={!pdfDoc}
              />
            </label>
            <label className="field">
              Zoom
              <input
                type="range"
                min={0.8}
                max={2}
                step={0.05}
                value={zoom}
                onChange={(event) => setZoom(Number(event.target.value))}
              />
              <span className="value">{zoom.toFixed(2)}x</span>
            </label>
          </div>

          <div className="panel">
            <h3>Auto Flip</h3>
            <label className="toggle">
              <input
                type="checkbox"
                checked={autoFlip}
                onChange={(event) => setAutoFlip(event.target.checked)}
              />
              Enable auto flip
            </label>
            <div className="meta">
              <span>Estimated page:</span>
              <span>
                {estimatedPageSeconds
                  ? `${estimatedPageSeconds.toFixed(1)}s`
                  : "--"}
              </span>
            </div>
            <label className="field">
              Sync offset (sec)
              <input
                type="number"
                step={0.5}
                value={pageOffset}
                onChange={(event) => setPageOffset(Number(event.target.value))}
              />
            </label>
            <label className="field">
              Sync speed
              <input
                type="range"
                min={0.7}
                max={1.3}
                step={0.01}
                value={syncSpeed}
                onChange={(event) => setSyncSpeed(Number(event.target.value))}
              />
              <span className="value">{syncSpeed.toFixed(2)}x</span>
            </label>
          </div>

          <div className="panel">
            <h3>Chapters (M4B)</h3>
            {chapters.length === 0 && (
              <div className="meta">
                <span>Chapters:</span>
                <span>None detected</span>
              </div>
            )}
            {chapters.length > 0 && (
              <div className="chapter-list">
                {chapters.map((chapter) => (
                  <button
                    key={`${chapter.title}-${chapter.start}`}
                    type="button"
                    className="chapter-item"
                    onClick={() => {
                      const audio = audioRef.current;
                      if (!audio) return;
                      audio.currentTime = chapter.start;
                      audio.play().catch(() => undefined);
                    }}
                  >
                    <span>{chapter.title}</span>
                    <span>{formatTime(chapter.start)}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </aside>

        <main className="viewer">
          {error && <div className="error">{error}</div>}
          {!pdfDoc && !isLoadingPdf && (
            <div className="empty-state">
              Load a PDF and audio file to start.
            </div>
          )}
          {isLoadingPdf && <div className="empty-state">Loading PDF…</div>}
          {pdfDoc && (
            <div className="reader-stage">
              <canvas ref={canvasRef} />
              {isRendering && <div className="rendering">Rendering…</div>}
            </div>
          )}
        </main>
      </section>
    </div>
  );
}

