import { asset } from '$app/paths';

export const ssr = false;
export const prerender = true;

export async function load({ fetch }) {
  const [metaResp, neighResp] = await Promise.all([
    fetch(asset('/data/europeana_metadata.json')),
    fetch(asset('/data/europeana_neighbors.json'))
  ]);
  return {
    metadata: await metaResp.json(),
    neighbors: await neighResp.json()
  };
}
