export const prerender = true;

export async function load({ fetch }) {
  const [metaResp, neighResp] = await Promise.all([
    fetch('/data/europeana_metadata.json'),
    fetch('/data/europeana_neighbors.json')
  ]);
  return {
    metadata: await metaResp.json(),
    neighbors: await neighResp.json()
  };
}
