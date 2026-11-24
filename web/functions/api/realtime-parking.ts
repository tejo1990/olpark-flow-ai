// Cloudflare Pages Function (Zero-cost serverless proxy for 2028 continuous operation)
export async function onRequestGet(): Promise<Response> {
  try {
    const upstream = await fetch(
      'https://www.ksponco.or.kr/online/main/parkingorsApi.do?apiKey=PARKING21803504',
      { headers: { 'User-Agent': 'OlparkFlowAI/1.0' } }
    );
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'public, max-age=60',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
