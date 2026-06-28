import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = process.env.INTERNAL_API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${PYTHON_API}/api/sources`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json([], { status: 200 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${PYTHON_API}/api/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: 201 });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
