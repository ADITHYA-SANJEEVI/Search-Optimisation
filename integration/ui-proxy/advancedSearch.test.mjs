import { test } from 'node:test'
import assert from 'node:assert/strict'
import { tryAdvancedSearch } from './advancedSearch.ts'

const base = { enabled: true, url: 'http://advanced/v1/search', timeout: 3000,
  publicUrl: 'https://sphere/publicContent/v1/search', headers: {},
  body: { request: { query: 'pregnancy', filters: { status: ['Live'] }, limit: 3, offset: 2 } } }

test('forward pagination, fetch exact IDs and reorder; omit missing/extra IDs', async () => {
  const calls = []
  const result = await tryAdvancedSearch({ ...base, http: async options => {
    calls.push(options)
    return { data: calls.length === 1 ? { ids: ['do_b', 'do_a', 'do_missing'], total: 9 } :
      { responseCode: 'OK', result: { content: [{ identifier: 'do_a' }, { identifier: 'do_extra' }, { identifier: 'do_b' }], facets: [] } } }
  } })
  assert.deepEqual(result.result.content.map(r => r.identifier), ['do_b', 'do_a'])
  assert.equal(result.result.count, 9)
  assert.deepEqual(calls[0].data, { query: 'pregnancy', filters: { status: ['Live'] }, limit: 3, offset: 2 })
  assert.deepEqual(calls[1].data.request.filters.identifier, ['do_b', 'do_a', 'do_missing'])
  assert.equal(calls[1].data.request.offset, 0)
  assert.equal(calls[1].data.request.sort_by, undefined)
})

for (const [name, change] of [['flag off', { enabled: false }], ['browse', { body: { request: { query: '' } } }],
  ['unsupported filter', { body: { request: { query: 'x', filters: { competency: true } } } }]]) {
  test(name + ' retains legacy behavior', async () => {
    let calls = 0
    assert.equal(await tryAdvancedSearch({ ...base, ...change, http: async () => { calls++; throw Error() } }), null)
    assert.equal(calls, 0)
  })
}

test('dependency failure invokes legacy fallback once without recursion', async () => {
  let calls = 0, fallback = 0
  const advanced = await tryAdvancedSearch({ ...base, http: async () => { calls++; throw Error('unavailable') } })
  const result = advanced || (++fallback && { legacy: true })
  assert.deepEqual(result, { legacy: true })
  assert.equal(calls, 1)
  assert.equal(fallback, 1)
})

test('empty ranked page does not fetch records and preserves total', async () => {
  let calls = 0
  const result = await tryAdvancedSearch({ ...base, http: async () => { calls++; return { data: { ids: [], total: 2 } } } })
  assert.equal(calls, 1)
  assert.deepEqual(result.result.content, [])
  assert.equal(result.result.count, 2)
})

test('malformed ranked response and record-fetch failure fall back', async () => {
  assert.equal(await tryAdvancedSearch({ ...base, http: async () => ({ data: { ids: ['x', 'x'], total: 2 } }) }), null)
  let calls = 0
  assert.equal(await tryAdvancedSearch({ ...base, http: async () => {
    if (++calls === 1) return { data: { ids: ['x'], total: 1 } }
    throw Error('fetch failure')
  } }), null)
  assert.equal(calls, 2)
})
