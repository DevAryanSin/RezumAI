import { useState, useMemo, useRef } from 'react'

type FileMeta = {
  file: File
  id: string
  progress: number
  error?: string
}

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
const MAX_FILES = 100

function formatBytes(n: number) {
  if (n === 0) return '0 B'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(n) / Math.log(1024))
  return `${(n / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`
}

export default function UploadBatchPage() {
  const [batchName, setBatchName] = useState('')
  const [files, setFiles] = useState<FileMeta[]>([])
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [batchId, setBatchId] = useState<string | null>(null)
  const xhrRef = useRef<XMLHttpRequest | null>(null)

  const totalBytes = useMemo(() => files.reduce((s, f) => s + f.file.size, 0), [files])

  function onFilesSelected(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null)
    const selected = e.target.files
    if (!selected) return
    const arr = Array.from(selected)

    if (files.length + arr.length > MAX_FILES) {
      setError(`Cannot select more than ${MAX_FILES} files in a batch.`)
      return
    }

    const validated: FileMeta[] = []
    for (const f of arr) {
      if (!f.name.toLowerCase().endsWith('.pdf') && f.type !== 'application/pdf') {
        setError(`Only PDF files are allowed. ${f.name} is not a PDF.`)
        continue
      }
      if (f.size > MAX_FILE_SIZE) {
        setError(`${f.name} exceeds max size of ${formatBytes(MAX_FILE_SIZE)}.`)
        continue
      }
      validated.push({ file: f, id: `${Date.now()}-${Math.random()}`, progress: 0 })
    }
    setFiles((cur) => [...cur, ...validated])

    // reset input so same file can be selected again
    e.currentTarget.value = ''
  }

  function removeFile(id: string) {
    if (uploading) return
    setFiles((cur) => cur.filter((f) => f.id !== id))
  }

  function genDefaultBatchName() {
    const now = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    return `batch-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  }

  function computePerFileProgress(loaded: number) {
    // Map total loaded to per-file progress
    let remaining = loaded
    const newFiles = files.map((f) => {
      const sz = f.file.size
      let p = 0
      if (remaining >= sz) {
        p = 100
        remaining -= sz
      } else if (remaining > 0) {
        p = Math.round((remaining / sz) * 100)
        remaining = 0
      }
      return { ...f, progress: p }
    })
    setFiles(newFiles)
  }

  function uploadAll() {
    setError(null)
    if (files.length === 0) {
      setError('Please select at least one PDF to upload.')
      return
    }
    setUploading(true)
    setBatchId(null)

    const name = batchName || genDefaultBatchName()

    const form = new FormData()
    form.append('batch_name', name)
    for (const f of files) {
      form.append('files', f.file, f.file.name)
    }

    const xhr = new XMLHttpRequest()
    xhrRef.current = xhr
    xhr.open('POST', 'http://localhost:8000/api/upload-batch')

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return
      const loaded = e.loaded
      const total = e.total
      const overall = Math.round((loaded / total) * 100)
      // update per-file progress proportionally
      computePerFileProgress(loaded)
    }

    xhr.onload = () => {
      setUploading(false)
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText)
          if (data.success) {
            setBatchId(data.batchId)
            setBatchName(name)
            setFiles((cur) => cur.map((f) => ({ ...f, progress: 100 })))
          } else {
            setError(data.message || 'Upload failed')
          }
        } catch (err: any) {
          setError('Failed to parse server response: ' + err?.message)
        }
      } else {
        try {
          const data = JSON.parse(xhr.responseText)
          setError(data.detail || data.message || `Upload failed with status ${xhr.status}`)
        } catch (_) {
          setError(`Upload failed with status ${xhr.status}`)
        }
      }
    }

    xhr.onerror = () => {
      setUploading(false)
      setError('Network error during upload')
    }

    xhr.send(form)
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Upload Batch — RezumAI</h1>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Batch name</label>
          <input
            value={batchName}
            onChange={(e) => setBatchName(e.target.value)}
            placeholder="Enter a batch name or leave empty to auto-generate"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="text-sm text-gray-500 mt-1">Or leave blank to generate a default name when uploading.</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Select PDF resumes</label>
          <input
            type="file"
            accept=".pdf,application/pdf"
            multiple
            onChange={onFilesSelected}
            disabled={uploading}
            className="mt-2"
          />
          <p className="text-sm text-gray-500 mt-1">Max {MAX_FILES} files per batch. Max size {formatBytes(MAX_FILE_SIZE)} per file.</p>
        </div>

        {files.length > 0 && (
          <div className="border rounded p-3 bg-white">
            <h3 className="font-medium">Files ({files.length})</h3>
            <ul className="mt-2 space-y-2">
              {files.map((f) => (
                <li key={f.id} className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{f.file.name}</div>
                    <div className="text-sm text-gray-500">{formatBytes(f.file.size)}</div>
                    <div className="w-64 bg-gray-100 h-2 rounded mt-2">
                      <div className="h-2 bg-indigo-500 rounded" style={{ width: `${f.progress}%` }} />
                    </div>
                  </div>
                  <div className="ml-4 flex-shrink-0">
                    <button
                      onClick={() => removeFile(f.id)}
                      disabled={uploading}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && <div className="text-red-600">{error}</div>}

        <div className="flex items-center space-x-3">
          <button
            onClick={uploadAll}
            disabled={uploading || files.length === 0}
            className={`px-4 py-2 rounded text-white ${uploading || files.length === 0 ? 'bg-gray-400' : 'bg-indigo-600 hover:bg-indigo-700'}`}
          >
            {uploading ? 'Uploading...' : 'Upload Batch'}
          </button>

          <button
            onClick={() => {
              setBatchName(genDefaultBatchName())
            }}
            className="px-3 py-2 rounded border"
          >
            Generate name
          </button>

          {batchId && (
            <div className="ml-auto text-sm">
              <div>Batch created: <span className="font-medium">{batchName}</span></div>
              <a href={`/batch/${batchId}`} className="text-indigo-600 hover:underline">Open Batch Dashboard</a>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
