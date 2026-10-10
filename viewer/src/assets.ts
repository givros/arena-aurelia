const applicationBase = new URL(import.meta.env.BASE_URL, document.baseURI);
const assetsBase = new URL('assets/', applicationBase);

export function assetURL(path: string): string {
  return new URL(path, assetsBase).href;
}
