import type { components } from './schema'

export type Document = components['schemas']['Document']
export type ChunkPage = components['schemas']['ChunkPage']
export type SeedPaper = components['schemas']['SeedPaper']
export type SeedResult = components['schemas']['SeedResult']
export type Health = components['schemas']['Health']
export type Chunk = components['schemas']['Chunk']
export type Citation = components['schemas']['Citation']
export type QueryResult = components['schemas']['QueryResult']

function messageFrom(body: unknown, fallback: string): string {
  if (typeof body === 'object' && body !== null && 'error' in body) {
    const error = body.error
    if (typeof error === 'object' && error !== null && 'message' in error && typeof error.message === 'string') {
      return error.message
    }
  }
  return fallback
}

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, { ...init, signal: init?.signal ?? AbortSignal.timeout(120_000) })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new Error('无法连接本地服务或请求超时，请检查后端是否运行，再重试。')
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw new Error(messageFrom(body, `服务返回错误（${response.status}），请稍后重试。`))
  if (body === null) throw new Error('本地服务未返回有效数据，请检查后端是否运行。')
  return body as T
}

export function uploadPdf(file: File, onProgress: (percent: number) => void): Promise<components['schemas']['IngestResult']> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/documents/upload')
    xhr.timeout = 120_000
    xhr.responseType = 'json'
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300 && xhr.response?.document) resolve(xhr.response)
      else reject(new Error(messageFrom(xhr.response, `上传失败（${xhr.status}），请重试。`)))
    }
    xhr.onerror = () => reject(new Error('无法连接本地服务，请检查后端是否运行。'))
    xhr.ontimeout = () => reject(new Error('上传或解析超时，可先刷新文档列表确认是否已导入。'))
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
}
