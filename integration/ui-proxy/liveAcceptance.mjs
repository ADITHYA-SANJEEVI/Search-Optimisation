// Read-only acceptance of the exact upstream helper against real service and public records.
import assert from 'node:assert/strict'
import { writeFile } from 'node:fs/promises'
import { tryAdvancedSearch } from './advancedSearch.ts'

const url = process.env.ADVANCED_SEARCH_URL || 'http://127.0.0.1:8017/v1/search'
const publicUrl = process.env.SPHERE_PUBLIC_SEARCH_URL
assert.ok(publicUrl, 'Set SPHERE_PUBLIC_SEARCH_URL')
const calls = []
let eligibleFetchedIds = []
const http = async options => {
  calls.push({ url: options.url, data: options.data })
  const response = await fetch(options.url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options.data), signal: AbortSignal.timeout(options.timeout) })
  assert.ok(response.ok)
  const data = await response.json()
  if (options.url === publicUrl) {
    data.result.content.reverse() // Deliberately perturb public fetch order.
    eligibleFetchedIds = data.result.content.filter(r => !r.competency).map(r => r.identifier)
  }
  return { data }
}
const body = { request: { query: 'pregnancy', filters: { primaryCategory: ['Course'], status: ['Live'] }, limit: 3, offset: 2 } }
const result = await tryAdvancedSearch({ enabled: true, url, timeout: 30000, publicUrl, headers: {}, body, http })
assert.ok(result, 'Advanced branch fell back unexpectedly')
assert.equal(calls.length, 2)
const rankedIds = calls[1].data.request.filters.identifier
assert.deepEqual(result.result.content.map(r => r.identifier), rankedIds.filter(id => eligibleFetchedIds.includes(id)))
const report = { timestamp: new Date().toISOString(), query: body.request.query, limit: 3, offset: 2,
  total: result.result.count, ordered_ids: result.result.content.map(r => r.identifier),
  omitted_ids: rankedIds.filter(id => !eligibleFetchedIds.includes(id)),
  omission_policy: 'Retain fetched records eligible under existing !competency rule; omit absent IDs',
  calls: calls.map(c => c.url), record_order_deliberately_reversed: true, passed: true }
await writeFile('artifacts/proxy_live_acceptance.json', JSON.stringify(report, null, 2))
console.log(JSON.stringify(report))
