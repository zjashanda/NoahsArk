export const fixture = {
  label: "DRAFT · PROTOTYPE",
  source: "prototype-fixture",
  schemaVersion: "0.1",
  serverAuthoritative: false,
  task: {
    id: "task-aurora-041",
    title: "Wake-word recovery under interrupted transport",
    revision: "R-7",
    stage: "Evidence review",
    mode: "formal",
    owner: "Review queue",
    updated: "Last authoritative update: 09:42 UTC",
    known: "Last known node activity: 09:37 UTC",
    axes: [
      ["Execution", "COMPLETED", "executed"],
      ["Validity", "VALID", "pass"],
      ["Business verdict", "PASS", "pass"],
      ["Evidence", "INCOMPLETE", "warning"],
      ["Verification", "NOT_RUN", "neutral"]
    ],
    evidence: { expected: 12, received: 12, verified: 9 },
    signals: [
      ["Communication", "OFFLINE", "neutral"],
      ["Occupancy", "OCCUPIED", "active"],
      ["Permit", "GRANTED", "active"],
      ["Release", "HELD", "warning"]
    ]
  },
  queue: [
    ["STOP delivery awaiting node recovery", "BLOCKED", "warning"],
    ["Node projection retained after heartbeat loss", "OFFLINE", "neutral"],
    ["Evidence bundle received; three items unverified", "PARTIAL EVIDENCE", "warning"],
    ["Device cleanup receipt is unavailable", "STALE", "neutral"]
  ],
  summary: [
    ["Needs attention", "04"], ["Running or held", "02"], ["Evidence gaps", "03"], ["Unknown progress", "01"]
  ],
  gates: ["G0 PASS", "G1 PASS", "G2 PASS", "G3 PASS", "G4 PASS", "G5 PASS", "G6 BLOCKED", "G7 PENDING"],
  tasks: [
    { id:"NA-2048", title:"Voice wake-word regression", stage:"Formal sampling", mode:"formal", state:"OFFLINE", stale:"STALE · 18 min", progress:"UNKNOWN", gate:"BLOCKED", gateOwner:"Mina / node ops", axes:["COMPLETED","VALID","PASS","INCOMPLETE","NOT_RUN"], evidence:[42,39,31], note:"Node communication is OFFLINE while execution remains RUNNING, occupancy OCCUPIED, and permit GRANTED." },
    { id:"NA-2042", title:"Speaker handoff baseline", stage:"Evidence review", mode:"smoke", state:"ONLINE", stale:"Updated 2 min ago", progress:"12 / 12 cases", gate:"PASSED", gateOwner:"—", axes:["COMPLETED","VALID","EXPECTED","COMPLETE","PASS"], evidence:[18,18,18], note:"COMPLETED is an execution fact; it is distinct from a business PASS." },
    { id:"NA-2037", title:"Far-field capture sweep", stage:"Plan & cases", mode:"formal", state:"ONLINE", stale:"Updated 6 min ago", progress:"UNKNOWN", gate:"PENDING", gateOwner:"Review queue", axes:["RUNNING","UNKNOWN","NOT_EVALUATED","UNVERIFIED","NOT_RUN"], evidence:[27,"UNKNOWN",0], note:"Total approved denominator is unknown, so progress stays UNKNOWN rather than becoming a percentage." }
  ]
};
