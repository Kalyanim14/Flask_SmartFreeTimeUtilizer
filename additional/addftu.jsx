import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import History from "./History";

const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "https://flask-smartfreetimeutilizer-j9rh.onrender.com"
    : "http://localhost:5000";

const TimeUtilizer = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: "",
    age: "",
    domain: "",
    topic: "",
    time_available: "",
    context: "",
  });

  // --- UPDATED PARSER: supports Title / Description / Small Tips (+ legacy Why/Build/Resources) ---
  function parseTasks(text) {
  if (!text || typeof text !== "string") return { intro: "", tasks: [], proTip: "" };

  // normalize
  const normalized = text.replace(/\r\n/g, "\n").trim();

  // capture optional trailing Pro Tip
  let proTip = "";
  const proTipMatch = normalized.match(/Pro Tip:\s*([\s\S]*)$/i);
  let core = normalized;
  if (proTipMatch) {
    proTip = proTipMatch[1].trim();
    core = normalized.replace(proTipMatch[0], "").trim();
  }
  if (!core) return { intro: "", tasks: [], proTip };

  // split into blocks using --- separators (common in your example)
  const rawBlocks = core.split(/\n-{3,}\n/).map((b) => b.trim()).filter(Boolean);

  // helper to detect heading line (Micro-Task X, ### Heading, or first-line title)
  function detectHeading(block) {
    const lines = block.split("\n").map((l) => l.trim());
    // Micro-Task like "Micro-Task 2" or "Micro Task 2"
    const microMatch = lines[0].match(/^(Micro[- ]?Task\b.*)$/i);
    if (microMatch) return { heading: microMatch[1], body: lines.slice(1).join("\n").trim() };
    // Markdown heading "### Title"
    const mdMatch = lines[0].match(/^###\s*(.+)$/);
    if (mdMatch) return { heading: mdMatch[1].trim(), body: lines.slice(1).join("\n").trim() };
    // if first line looks like a short title (no colon and short), treat it as heading
    if (lines.length > 1 && lines[0].length <= 60 && !lines[0].includes(":")) {
      return { heading: lines[0], body: lines.slice(1).join("\n").trim() };
    }
    // otherwise no explicit heading
    return { heading: "", body: block };
  }

  // if the first block is not a task (no heading and contains multiple paragraphs), treat as intro
  let intro = "";
  const blocks = [];
  if (rawBlocks.length && detectHeading(rawBlocks[0]).heading === "" && rawBlocks[0].split("\n").length > 3) {
    intro = rawBlocks[0];
    rawBlocks.slice(1).forEach((b) => blocks.push(detectHeading(b)));
  } else {
    rawBlocks.forEach((b) => blocks.push(detectHeading(b)));
  }

  // parse each block into task object
  const tasks = blocks.map(({ heading, body }) => {
    const titleFromHeading = heading || "";

    // Title (explicit or from heading)
    const titleMatch = body.match(/^\s*Title\s*:?\s*(.+)$/im);
    const title = (titleMatch ? titleMatch[1].trim() : titleFromHeading || "Task").trim();

    // Description (stop at next known section)
    const descMatch = body.match(/Description\s*:?\s*([\s\S]*?)(?=\n(?:Small Tips|Why|Build|Resources)\b|$)/i);
    const description = descMatch ? descMatch[1].trim() : "";

    // Small Tips (may appear multiple times) — collect all appearances and dedupe preserving order
    const tipsAll = [];
    const smallTipsRegex = /Small Tips\s*:?\s*([\s\S]*?)(?=\n(?:Why|Build|Resources|$))/ig;
    let m;
    while ((m = smallTipsRegex.exec(body)) !== null) {
      const blockLines = m[1]
        .split("\n")
        .map((l) => l.trim())
        .filter((l) => l.length > 0)
        .map((l) => l.replace(/^[-*•\s]+/, ""));
      blockLines.forEach((ln) => tipsAll.push(ln));
    }
    // dedupe while preserving order
    const seen = new Set();
    const tips = tipsAll.filter((t) => {
      if (!t) return false;
      const key = t.replace(/\s+/g, " ").trim().toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // Legacy sections (back-compat)
    const whyMatch = body.match(/Why\s*:?\s*([\s\S]*?)(?=\n(?:Build|Resources|Small Tips)\b|$)/i);
    const buildMatch = body.match(/Build\s*:?\s*([\s\S]*?)(?=\n(?:Resources|Small Tips)\b|$)/i);
    const resourcesMatch = body.match(/Resources\s*:?\s*([\s\S]*)/i);

    return {
      title,
      description,
      tips,
      why: whyMatch ? whyMatch[1].trim() : "",
      build: buildMatch ? buildMatch[1].trim() : "",
      resources: resourcesMatch ? resourcesMatch[1].trim() : "",
    };
  });

  return { intro, tasks, proTip };
}


  const [customInputs, setCustomInputs] = useState({
    domain: "",
    topic: "",
    time_available: "",
  });
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [displayName, setDisplayName] = useState("");

  useEffect(() => {
    const storedName = localStorage.getItem("name") || "";
    const storedUsername = localStorage.getItem("username") || "";
    setDisplayName(storedName || storedUsername || "");
    setFormData((d) => ({ ...d, name: storedName || d.name }));
  }, []);

  const dropdownOptions = {
    domain: [
      "Engineering Student",
      "Software Developer",
      "Teacher",
      "Hardware Engineer",
      "Data Analyst",
      "Other",
    ],
    topic: [
      "Programming",
      "Productivity",
      "Career Guidance",
      "Study Tips",
      "Health & Fitness",
      "Other",
    ],
    time_available: ["15 minutes", "30 minutes", "1 hour", "2+ hours", "Other"],
  };

  const handleChange = (e) =>
    setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleDropdownChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (value !== "Other") {
      setCustomInputs((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const handleCustomChange = (e) => {
    const { name, value } = e.target;
    setCustomInputs((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResponse("");

    try {
      const username = localStorage.getItem("username") || "";

      // Final payload with custom inputs for "Other"
      const finalData = { ...formData };
      Object.keys(dropdownOptions).forEach((key) => {
        if (formData[key] === "Other" && customInputs[key]) {
          finalData[key] = customInputs[key];
        }
      });

      const payload = { ...finalData, username };
      const res = await axios.post(`${API_BASE_URL}/api/process-data`, payload);
      setResponse(res.data.response || "No response returned.");
      // Auto-scroll to output
      setTimeout(() => {
        document.getElementById("output-box")?.scrollIntoView({ behavior: "smooth" });
      }, 50);
    } catch (err) {
      console.error(err);
      setResponse("⚠ Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem("username");
    localStorage.removeItem("name");
    setIsLoggedIn(false);
    navigate("/signin");
  };

  const clearResponse = () => setResponse("");

  const initials = (name) =>
    name
      ? name
          .split(" ")
          .map((p) => p[0])
          .slice(0, 2)
          .join("")
          .toUpperCase()
      : "";

  // Parse response once (avoid parsing in JSX)
  const parsedResponse = response ? parseTasks(response) : null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 via-white to-white font-poppins text-[1rem] leading-relaxed">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-sm border-b border-green-100">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-700 text-white flex items-center justify-center font-semibold text-lg shadow">
              SF
            </div>
            <div>
              <h1 className="text-xl font-semibold text-green-800">
                Smart Free Time Utilizer
              </h1>
              <p className="text-sm text-green-600">
                Personalized micro-learning plans
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Link
              to="/timeutilizer"
              className="hidden md:inline-block px-4 py-2 rounded-lg hover:bg-green-100 text-green-700 text-base"
            >
              Home
            </Link>
            <Link
              to="/history"
              className="px-4 py-2 rounded-lg bg-white border border-green-200 hover:shadow-sm text-green-700 text-base"
            >
              History
            </Link>
            <div className="flex items-center gap-3 ml-4">
              <div className="w-9 h-9 rounded-full bg-green-700 text-white flex items-center justify-center font-medium text-lg">
                {initials(displayName)}
              </div>
              <div className="text-right">
                <div className="text-base font-medium text-green-800">
                  {displayName}
                </div>
                <button
                  onClick={handleLogout}
                  className="text-sm text-red-600 hover:underline"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-3xl mx-auto px-6 py-10 flex flex-col gap-10">
        {/* Form */}
        <section className="bg-white rounded-2xl shadow-md p-8">
          <h2 className="text-2xl font-semibold text-green-800 mb-3">
            Welcome{displayName ? `, ${displayName}` : ""}! 👋
          </h2>
          <p className="text-green-700 mb-8 text-base">
            Let’s make the most of your free time. Fill in your preferences
            below for a tailored guide.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name & Age */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-green-800 font-medium text-sm">Name</label>
                <input
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Your name"
                  className="w-full border border-green-200 rounded-xl px-3 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-green-300"
                />
              </div>
              <div>
                <label className="text-green-800 font-medium text-sm">Age</label>
                <input
                  name="age"
                  type="number"
                  value={formData.age}
                  onChange={handleChange}
                  placeholder="Age"
                  className="w-full border border-green-200 rounded-xl px-3 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-green-300"
                />
              </div>
            </div>

            {/* Dropdown Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.keys(dropdownOptions).map((key) => (
                <div key={key}>
                  <label className="text-green-800 font-medium text-sm capitalize">
                    {key.replace("_", " ")}
                  </label>
                  <select
                    name={key}
                    value={formData[key]}
                    onChange={handleDropdownChange}
                    className="w-full border border-green-200 rounded-xl px-3 py-2.5 text-base bg-white focus:outline-none focus:ring-2 focus:ring-green-300"
                  >
                    <option value="">Select {key.replace("_", " ")}</option>
                    {dropdownOptions[key].map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>

                  {formData[key] === "Other" && (
                    <input
                      type="text"
                      name={key}
                      value={customInputs[key]}
                      onChange={handleCustomChange}
                      placeholder={`Enter custom ${key.replace("_", " ")}`}
                      className="mt-2 w-full border border-green-200 rounded-xl px-3 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-green-300"
                    />
                  )}
                </div>
              ))}
            </div>

            {/* Context */}
            <div>
              <label className="text-green-800 font-medium text-sm">
                Context (optional)
              </label>
              <textarea
                name="context"
                value={formData.context}
                onChange={handleChange}
                placeholder="Add details or preferences..."
                rows="3"
                className="w-full border border-green-200 rounded-xl px-3 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-green-300"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-3 mt-2 font-semibold rounded-xl text-white text-lg shadow-md transition-all duration-300 ${
                loading
                  ? "bg-green-300 cursor-not-allowed"
                  : "bg-green-700 hover:bg-green-800"
              }`}
            >
              {loading ? "Generating..." : "Generate Plan"}
            </button>
          </form>
        </section>

        {/* Output */}
        <section className="flex flex-col gap-4">
          <div className="bg-white rounded-2xl shadow-md p-8 flex flex-col">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-green-800">Personalized Result</h3>
              <div className="flex gap-3">
                <button
                  onClick={() => response && navigator.clipboard.writeText(response)}
                  className="text-green-700 bg-green-100 hover:bg-green-200 px-4 py-2 rounded-lg text-sm font-medium"
                >
                  Copy
                </button>
                <button
                  onClick={clearResponse}
                  className="text-red-600 bg-red-100 hover:bg-red-200 px-4 py-2 rounded-lg text-sm font-medium"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="mt-5">
              <div
                id="output-box"
                className="border border-green-100 rounded-xl bg-green-50/50 p-6 max-h-[70vh] overflow-y-auto"
              >
                {loading ? (
                  <p className="text-green-700 text-lg animate-pulse">
                    ⏳ Generating your personalized suggestions...
                  </p>
                ) : response && parsedResponse ? (
                  <div className="space-y-5">
                    {parsedResponse.intro && <p className="text-base">{parsedResponse.intro}</p>}

                    {parsedResponse.tasks.map((t, i) => (
                      <div key={i} className="border-l-4 border-green-500 pl-4">
                        <h3 className="text-lg font-semibold text-green-800">{t.title}</h3>

                        {/* NEW: Description & Small Tips */}
                        {t.description && (
                          <p className="mt-2 whitespace-pre-line">
                            <strong>Description:</strong> {t.description}
                          </p>
                        )}

                        {t.tips && t.tips.length > 0 && (
                          <div className="mt-2">
                            <strong>Small Tips:</strong>
                            <ul className="list-disc ml-6 mt-1 space-y-1">
                              {t.tips.map((tip, j) => (
                                <li key={j}>{tip}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Legacy sections (still supported) */}
                        {t.why && <p className="mt-2"><strong>Why:</strong> {t.why}</p>}
                        {t.build && (
                          <p className="mt-2 whitespace-pre-line"><strong>Build:</strong> {t.build}</p>
                        )}
                        {t.resources && (
                          <p className="text-sm text-green-700 mt-2">
                            <strong>Resources:</strong><br />{t.resources}
                          </p>
                        )}
                      </div>
                    ))}

                    {parsedResponse.proTip && (
                      <p className="italic text-gray-600">💡 {parsedResponse.proTip}</p>
                    )}
                  </div>
                ) : (
                  <p className="text-green-700 text-base italic">
                    Your personalized guide will appear here!
                  </p>
                )}
              </div>
            </div>

            <div className="mt-5 flex justify-between items-center text-sm text-green-700">
              <Link to="/history" className="hover:underline font-medium">
                View full history →
              </Link>
              <p className="text-gray-500">Smart. Simple. Productive.</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default TimeUtilizer;
