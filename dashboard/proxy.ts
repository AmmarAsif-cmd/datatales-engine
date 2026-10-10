import { NextResponse, type NextRequest } from "next/server";

// Only answer requests addressed to this machine. Blocks DNS-rebinding style access from
// other sites even if the port were reachable. (Server Actions also check Origin vs Host.)
const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]"]);

export function proxy(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").replace(/:\d+$/, "").toLowerCase();
  if (!LOCAL_HOSTS.has(host)) {
    return new NextResponse("DataTales dashboard is local-only.", { status: 403 });
  }
  return NextResponse.next();
}
