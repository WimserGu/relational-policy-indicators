const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const ROOT = path.resolve(__dirname, '..', '..');
const PHASE3 = path.join(ROOT, 'results', 'replication_run', 'cross_sectional');
const OUT = path.join(ROOT, 'results', 'replication_run', 'fixed_degree_null');
fs.mkdirSync(OUT, {recursive: true});

const payload = JSON.parse(fs.readFileSync(path.join(PHASE3, 'processed', 'e3_null_inputs.json'), 'utf8'));
const oldDiagnostics = JSON.parse(fs.readFileSync(path.join(ROOT, 'results', 'diagnostics', 'archived_knowledge_null_schedule_basis.json'), 'utf8'));

class XorShift32 {
  constructor(seed) { this.state = (seed >>> 0) || 0x9e3779b9; }
  nextUint() {
    let x = this.state;
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    this.state = x >>> 0;
    return this.state;
  }
  index(n) {
    const range = 0x100000000;
    const limit = Math.floor(range / n) * n;
    let x;
    do { x = this.nextUint(); } while (x >= limit);
    return x % n;
  }
}

function degreeSequence(n, u, v) {
  const degree = new Int32Array(n);
  for (let e = 0; e < u.length; e++) { degree[u[e]]++; degree[v[e]]++; }
  return Array.from(degree);
}

function adjacencyKey(n, adjacency) {
  const key = Buffer.allocUnsafe(n * (n - 1) / 2);
  let k = 0;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) key[k++] = adjacency[i * n + j];
  }
  return key.toString('base64');
}

function advanceProposalSteps(target, n, u, v, adjacency, rng, counter) {
  const E = u.length;
  for (let step = 0; step < target; step++) {
    counter.proposals++;
    const e1 = rng.index(E);
    const e2 = rng.index(E);
    if (e1 === e2) { counter.rejectedSameEdge++; continue; }
    const a = u[e1], b = v[e1], c = u[e2], d = v[e2];
    if (a === c || a === d || b === c || b === d) {
      counter.rejectedSharedEndpoint++;
      continue;
    }
    let x1, y1, x2, y2;
    if ((rng.nextUint() & 1) === 0) {
      x1 = a; y1 = c; x2 = b; y2 = d;
    } else {
      x1 = a; y1 = d; x2 = b; y2 = c;
    }
    if (adjacency[x1 * n + y1] || adjacency[x2 * n + y2]) {
      counter.rejectedDuplicateEdge++;
      continue;
    }
    adjacency[a * n + b] = 0; adjacency[b * n + a] = 0;
    adjacency[c * n + d] = 0; adjacency[d * n + c] = 0;
    adjacency[x1 * n + y1] = 1; adjacency[y1 * n + x1] = 1;
    adjacency[x2 * n + y2] = 1; adjacency[y2 * n + x2] = 1;
    u[e1] = x1; v[e1] = y1; u[e2] = x2; v[e2] = y2;
    counter.accepted++;
  }
}

function autocorrelation(values, lag) {
  const n = values.length;
  if (lag >= n) return null;
  const mean = values.reduce((a, b) => a + b, 0) / n;
  let denominator = 0;
  for (const value of values) denominator += (value - mean) ** 2;
  if (denominator === 0) return 0;
  let numerator = 0;
  for (let i = 0; i < n - lag; i++) numerator += (values[i] - mean) * (values[i + lag] - mean);
  return numerator / denominator;
}

function effectiveSampleSize(values, maxLag = 200) {
  const n = values.length;
  let sum = 0;
  for (let lag = 1; lag <= Math.min(maxLag, n - 2); lag += 2) {
    const pair = autocorrelation(values, lag) + autocorrelation(values, lag + 1);
    if (!(pair > 0)) break;
    sum += pair;
  }
  return n / Math.max(1 + 2 * sum, 1);
}

function runChain(chainId, graph, n, rec, rec2021, retainedDraws, burnProposals, spacingProposals, seed) {
  const E = graph.edges.length;
  const u = Int32Array.from(graph.edges.map(edge => edge[0]));
  const v = Int32Array.from(graph.edges.map(edge => edge[1]));
  const weights = Float64Array.from(graph.weights);
  const totalWeight = Array.from(weights).reduce((a, b) => a + b, 0);
  const adjacency = new Uint8Array(n * n);
  for (let e = 0; e < E; e++) {
    adjacency[u[e] * n + v[e]] = 1;
    adjacency[v[e] * n + u[e]] = 1;
  }
  const degreeStart = degreeSequence(n, u, v);
  const topologyRng = new XorShift32(seed);
  const weightRng = new XorShift32((seed ^ 0xa5a5a5a5) >>> 0);
  const counter = {
    proposals: 0, accepted: 0, rejectedSameEdge: 0,
    rejectedSharedEndpoint: 0, rejectedDuplicateEdge: 0,
  };

  advanceProposalSteps(burnProposals, n, u, v, adjacency, topologyRng, counter);
  const rows = [];
  const within = [];
  const within2021 = [];
  const seen = new Set();
  const shuffled = new Float64Array(E);
  for (let draw = 0; draw < retainedDraws; draw++) {
    advanceProposalSteps(spacingProposals, n, u, v, adjacency, topologyRng, counter);
    let binary = 0, binary2021 = 0;
    for (let e = 0; e < E; e++) {
      binary += rec[u[e] * n + v[e]];
      binary2021 += rec2021[u[e] * n + v[e]];
      shuffled[e] = weights[e];
    }
    binary /= E;
    binary2021 /= E;
    within.push(binary);
    within2021.push(binary2021);

    for (let e = E - 1; e > 0; e--) {
      const j = weightRng.index(e + 1);
      const tmp = shuffled[e]; shuffled[e] = shuffled[j]; shuffled[j] = tmp;
    }
    let weighted = 0, weighted2021 = 0;
    for (let e = 0; e < E; e++) {
      weighted += rec[u[e] * n + v[e]] * shuffled[e];
      weighted2021 += rec2021[u[e] * n + v[e]] * shuffled[e];
    }
    rows.push({
      chain: chainId,
      draw_in_chain: draw + 1,
      within_end2025: binary,
      within_start2021: binary2021,
      weighted_end2025: weighted / totalWeight,
      weighted_start2021: weighted2021 / totalWeight,
    });
    seen.add(adjacencyKey(n, adjacency));
    if ((draw + 1) % 1000 === 0) process.stdout.write(`chain ${chainId}: ${draw + 1}/${retainedDraws}\n`);
  }

  const degreeEnd = degreeSequence(n, u, v);
  const diagnostics = {
    chain: chainId,
    seed,
    retained_draws: retainedDraws,
    burn_in_proposal_steps: burnProposals,
    proposal_steps_between_draws: spacingProposals,
    total_proposals: counter.proposals,
    accepted_swaps: counter.accepted,
    rejected_proposals: counter.proposals - counter.accepted,
    rejected_same_edge: counter.rejectedSameEdge,
    rejected_shared_endpoint: counter.rejectedSharedEndpoint,
    rejected_duplicate_edge: counter.rejectedDuplicateEdge,
    acceptance_rate: counter.accepted / counter.proposals,
    unique_retained_adjacencies: seen.size,
    degree_preserved: degreeStart.every((value, index) => value === degreeEnd[index]),
    autocorrelation_end2025: {
      lag_1: autocorrelation(within, 1), lag_5: autocorrelation(within, 5),
      lag_10: autocorrelation(within, 10), lag_20: autocorrelation(within, 20),
    },
    effective_sample_size_end2025: effectiveSampleSize(within),
    effective_sample_size_start2021: effectiveSampleSize(within2021),
  };
  return {rows, within, diagnostics};
}

function rHat(chains) {
  const m = chains.length;
  const n = chains[0].length;
  const means = chains.map(values => values.reduce((a, b) => a + b, 0) / n);
  const variances = chains.map((values, index) => values.reduce((sum, value) => sum + (value - means[index]) ** 2, 0) / (n - 1));
  const grand = means.reduce((a, b) => a + b, 0) / m;
  const B = n * means.reduce((sum, value) => sum + (value - grand) ** 2, 0) / (m - 1);
  const W = variances.reduce((a, b) => a + b, 0) / m;
  const varianceHat = ((n - 1) / n) * W + B / n;
  return Math.sqrt(varianceHat / W);
}

function csvEscape(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

const n = payload.nodes.length;
const graph = payload.graphs.knowledge;
const rec = Int8Array.from(payload.rec);
const rec2021 = Int8Array.from(payload.rec2021);
const totalRetained = Number(payload.draws);
const chainsN = 2;
const retainedPerChain = totalRetained / chainsN;
if (!Number.isInteger(retainedPerChain)) throw new Error('Retained draws must divide equally across chains');

const baselineAcceptance = Number(oldDiagnostics.acceptance_rate);
const burnProposals = Math.ceil((100 * graph.edges.length) / baselineAcceptance);
const spacingProposals = Math.ceil((20 * graph.edges.length) / baselineAcceptance);
const seeds = [Number(graph.seed) >>> 0, (Number(graph.seed) ^ 0x6d2b79f5) >>> 0];
const runs = seeds.map((seed, index) => runChain(
  index + 1, graph, n, rec, rec2021, retainedPerChain,
  burnProposals, spacingProposals, seed,
));
const rows = runs.flatMap(run => run.rows);

const header = ['chain', 'draw_in_chain', 'within_end2025', 'within_start2021', 'weighted_end2025', 'weighted_start2021'];
const csv = [header.join(','), ...rows.map(row => header.map(field => csvEscape(row[field])).join(','))].join('\n') + '\n';
fs.writeFileSync(path.join(OUT, 'knowledge_uniform_switch_chain_draws.csv.gz'), zlib.gzipSync(csv));

const diagnostics = {
  graph: 'knowledge',
  target_distribution: 'Uniform over reachable undirected simple graphs with the observed degree sequence.',
  proposal_mechanism: 'Choose two edge indices uniformly with unbiased integer sampling; choose one of the two endpoint pairings with probability 1/2.',
  acceptance_rule: 'Accept only disjoint-edge proposals that create two absent simple-graph edges.',
  invalid_proposals: 'Retained as self-loops and counted as proposal steps.',
  stationary_distribution_reason: 'The proposal kernel is symmetric; retained rejection self-loops make the uniform fixed-degree distribution stationary and ensure aperiodicity.',
  nodes: n,
  edges: graph.edges.length,
  chains: chainsN,
  retained_draws_total: totalRetained,
  retained_draws_per_chain: retainedPerChain,
  burn_in_proposal_steps: burnProposals,
  proposal_steps_between_draws: spacingProposals,
  schedule_basis: `Converted the registered 100E/20E accepted-swap schedule to fixed proposal time using the archived acceptance rate ${baselineAcceptance}.`,
  rhat_within_end2025: rHat(runs.map(run => run.within)),
  chain_diagnostics: runs.map(run => run.diagnostics),
};
fs.writeFileSync(path.join(OUT, 'knowledge_uniform_switch_chain_diagnostics.json'), JSON.stringify(diagnostics, null, 2));
process.stdout.write(JSON.stringify(diagnostics, null, 2) + '\n');
