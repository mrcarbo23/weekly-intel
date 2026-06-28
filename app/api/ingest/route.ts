import { NextResponse } from "next/server";

const PYTHON_API = process.env.INTERNAL_API_URL || "http://localhost:8000";

export async function POST() {
  try {
    const res = await fetch(`${PYTHON_API}/api/ingest`, { method: "POST" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
