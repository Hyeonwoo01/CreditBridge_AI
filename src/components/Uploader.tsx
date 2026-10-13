import { useRef, useState, type DragEvent } from 'react';
import { SAMPLES } from '../data/samples';
import { pdfToText } from '../lib/pdf';
import { Text, Upload } from './Icons';

interface Props {
  busy: string[];
  onAdd: (text: string, fileName: string) => Promise<void>;
  usedSamples: Set<string>;
}

async function readFile(file: File): Promise<string> {
  if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) return pdfToText(file);
  return file.text();
}

export function Uploader({ busy, onAdd, usedSamples }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<'file' | 'text'>('file');
  const [dragging, setDragging] = useState(false);
  const [pasted, setPasted] = useState('');
  const [error, setError] = useState('');

  async function handleFiles(files: FileList | File[]) {
    setError('');
    for (const file of Array.from(files)) {
      try {
        const text = await readFile(file);
        if (text.replace(/\s/g, '').length < 80) {
          setError(`${file.name}: 글자를 읽을 수 없어요. 스캔한 PDF라면 '텍스트 붙여넣기'를 이용해 주세요.`);
          continue;
        }
        await onAdd(text, file.name);
      } catch {
        setError(`${file.name}: 파일을 열 수 없어요. PDF 또는 텍스트 파일인지 확인해 주세요.`);
      }
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) void handleFiles(e.dataTransfer.files);
  }

  async function submitText() {
    if (pasted.trim().length < 80) {
      setError('강의계획서 내용을 조금 더 붙여넣어 주세요. (주차별 일정, 학습 목표 등)');
      return;
    }
    setError('');
    await onAdd(pasted, '붙여넣은 강의계획서');
    setPasted('');
  }

  return (
    <section className="uploader" aria-label="강의계획서 추가">
      <div className="segmented" role="tablist">
        <button role="tab" aria-selected={mode === 'file'} className={mode === 'file' ? 'on' : ''} onClick={() => setMode('file')}>
          <Upload width={16} height={16} /> 파일 업로드
        </button>
        <button role="tab" aria-selected={mode === 'text'} className={mode === 'text' ? 'on' : ''} onClick={() => setMode('text')}>
          <Text width={16} height={16} /> 텍스트 붙여넣기
        </button>
      </div>

      {mode === 'file' ? (
        <div
          className={`dropzone${dragging ? ' dragging' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => input.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && input.current?.click()}
        >
          <div className="dropzone-icon">
            <Upload width={24} height={24} />
          </div>
          <p className="title-md">강의계획서(Syllabus)를 올려주세요</p>
          <p className="muted body-sm">PDF · TXT · 여러 과목을 한 번에 올릴 수 있어요</p>
          <input
            ref={input}
            type="file"
            accept=".pdf,.txt,.md,application/pdf,text/plain"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files) void handleFiles(e.target.files);
              e.target.value = '';
            }}
          />
        </div>
      ) : (
        <div className="paste">
          <textarea
            value={pasted}
            onChange={(e) => setPasted(e.target.value)}
            placeholder={'Course title, description, learning outcomes,\nWeek 1: ...\nWeek 2: ...'}
            rows={8}
          />
          <button className="btn btn-primary" onClick={submitText} disabled={!pasted.trim()}>
            분석하기
          </button>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}
      {busy.length > 0 && (
        <div className="busy">
          <span className="spinner" /> {busy[0]} 분석 중{busy.length > 1 ? ` 외 ${busy.length - 1}개` : ''}…
        </div>
      )}

      <div className="samples">
        <span className="caption muted">강의계획서가 없다면 샘플로 체험해 보세요</span>
        <div className="chips">
          {SAMPLES.map((s) => (
            <button key={s.id} className="chip" disabled={usedSamples.has(s.fileName)} onClick={() => void onAdd(s.text, s.fileName)}>
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
