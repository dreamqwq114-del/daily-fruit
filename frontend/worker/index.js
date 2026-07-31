export default {
  async fetch(request, env) {
    let response = await env.ASSETS.fetch(request)
    const acceptsHtml = request.headers.get('accept')?.includes('text/html')

    if (response.status === 404 && request.method === 'GET' && acceptsHtml) {
      const indexUrl = new URL('/index.html', request.url)
      response = await env.ASSETS.fetch(new Request(indexUrl, request))
    }

    const contentType = response.headers.get('content-type') ?? ''

    if (!contentType.includes('text/html')) {
      return response
    }

    const origin = new URL(request.url).origin
    const html = (await response.text()).replaceAll('__SITE_ORIGIN__', origin)

    return new Response(html, response)
  },
}
