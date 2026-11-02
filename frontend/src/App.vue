<script setup>
import { ref, computed, onMounted } from "vue";
import {
  LayoutDashboard, Gauge, GitCompare, Database, BrainCircuit,
  FileText, Settings, Bell, Search, ArrowUpRight, ChevronDown,
  Activity, Zap, Clock3, Menu, X, Sun, Moon, Upload, Download,
  CheckCircle2, AlertCircle, RefreshCw
} from "lucide-vue-next";

const API_BASE_URL = "http://127.0.0.1:8000";
const activeTab = ref("Overview");
const mobileMenu = ref(false);
const search = ref("");
const isDark = ref(false);
const apiStatus = ref("checking");

const navigation = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Engine Calculator", icon: Gauge },
  { name: "Engine Comparison", icon: GitCompare },
  { name: "Dataset Manager", icon: Database },
  { name: "AI Analyst", icon: BrainCircuit },
  { name: "Reports", icon: FileText }
];

const pageDescription = computed(() => ({
  "Overview": "A consolidated view of engine performance and analysis.",
  "Engine Calculator": "Calculate engine power from torque and rotational speed.",
  "Engine Comparison": "Compare two engine operating points using the same calculation model.",
  "Dataset Manager": "Upload, validate and inspect engine measurement CSV files.",
  "AI Analyst": "Review data-driven observations and engineering limitations.",
  "Reports": "Export calculation and dataset results.",
  "Settings": "Manage your local workspace preferences."
}[activeTab.value]));

const torqueInput = ref(200);
const rpmInput = ref(3000);
const calculationResult = ref(null);
const isCalculating = ref(false);
const calculationError = ref("");

const curveStartRpm = ref(1000);
const curveEndRpm = ref(6000);
const curveStep = ref(500);
const curveResult = ref(null);
const isLoadingCurve = ref(false);
const curveError = ref("");

const selectedDataset = ref(null);
const datasetResult = ref(null);
const datasetError = ref("");
const isUploadingDataset = ref(false);

const diagnosticFile = ref(null);
const diagnosticResult = ref(null);
const diagnosticError = ref("");
const isDiagnosing = ref(false);

const compareAFile = ref(null);
const compareBFile = ref(null);
const compareResult = ref(null);
const compareError = ref("");
const isComparing = ref(false);
const comparisonChartMode = ref("torque");

const comparisonRows = computed(() => {
  const result = compareResult.value;
  if (!result) return [];
  const a = result.engine_a.data;
  const b = result.engine_b.data;
  const rpmValues = [...new Set([...a, ...b].map(row => row.rpm))].sort((x, y) => x - y);
  const interpolate = (rows, rpm, key) => {
    const exact = rows.find(row => row.rpm === rpm);
    if (exact) return exact[key];
    if (rpm < rows[0].rpm || rpm > rows[rows.length - 1].rpm) return null;
    for (let i = 1; i < rows.length; i++) {
      if (rows[i].rpm > rpm) {
        const left = rows[i - 1], right = rows[i];
        const ratio = (rpm - left.rpm) / (right.rpm - left.rpm);
        return left[key] + ratio * (right[key] - left[key]);
      }
    }
    return null;
  };
  return rpmValues.map(rpm => ({
    rpm,
    a: interpolate(a, rpm, comparisonChartMode.value === "torque" ? "torque_nm" : "power_kw"),
    b: interpolate(b, rpm, comparisonChartMode.value === "torque" ? "torque_nm" : "power_kw")
  }));
});

const comparisonChartLines = computed(() => {
  const rows = comparisonRows.value;
  if (!rows.length) return { a: "", b: "" };
  const values = rows.flatMap(row => [row.a, row.b]).filter(value => value !== null && Number.isFinite(value));
  const maxValue = Math.max(...values, 1);
  const minRpm = rows[0].rpm;
  const maxRpm = rows[rows.length - 1].rpm;
  const makeLine = key => rows.filter(row => row[key] !== null).map(row => {
    const x = 48 + ((row.rpm - minRpm) / Math.max(maxRpm - minRpm, 1)) * 504;
    const y = 190 - (row[key] / maxValue) * 145;
    return `${x},${y}`;
  }).join(" ");
  return { a: makeLine("a"), b: makeLine("b") };
});

const filteredNavigation = computed(() => {
  if (!search.value.trim()) return navigation;
  return navigation.filter(item => item.name.toLowerCase().includes(search.value.toLowerCase()));
});

const metrics = [
  { label: "Peak torque", value: "200", unit: "Nm", detail: "Illustrative input", icon: Gauge },
  { label: "Calculated power", value: "62.83", unit: "kW", detail: "At 3,000 RPM", icon: Zap },
  { label: "Engine speed", value: "3,000", unit: "RPM", detail: "Operating point", icon: Activity },
  { label: "Power output", value: "84.27", unit: "HP", detail: "Calculated value", icon: Activity }
];

const sampleTorque = [90,112,135,153,168,180,185,182,174,160,143];
const samplePower = sampleTorque.map((torque, index) => torque * (1000 + index * 500) / 9549.2966);

function points(values, maxValue) {
  return values.map((value, index) => {
    const x = 45 + index * 49;
    const y = 190 - (value / maxValue) * 155;
    return `${x},${y}`;
  }).join(" ");
}

const curvePolyline = computed(() => {
  const rows = curveResult.value?.curve || [];
  if (rows.length < 2) return "";
  const maxPower = Math.max(...rows.map(row => row.power_kw), 1);
  return rows.map((row, index) => {
    const x = 48 + (index / (rows.length - 1)) * 504;
    const y = 190 - (row.power_kw / maxPower) * 145;
    return `${x},${y}`;
  }).join(" ");
});

const datasetRows = computed(() => datasetResult.value?.data || []);
const aiInsights = computed(() => {
  const insights = [];
  if (datasetResult.value) {
    insights.push(`The uploaded dataset contains ${datasetResult.value.records} valid records from ${datasetResult.value.rpm_min.toLocaleString()} to ${datasetResult.value.rpm_max.toLocaleString()} RPM.`);
    insights.push(`The highest torque value in this dataset is ${datasetResult.value.peak_torque_nm.toFixed(2)} Nm.`);
    insights.push(`The highest calculated or supplied power value is ${datasetResult.value.peak_power_kw.toFixed(2)} kW.`);
    insights.push("Check the source, units and test conditions before treating these measurements as comparable engine results.");
  } else if (calculationResult.value) {
    insights.push(`At ${calculationResult.value.rpm.toLocaleString()} RPM and ${calculationResult.value.torque_nm.toFixed(2)} Nm, calculated power is ${calculationResult.value.power_kw.toFixed(2)} kW.`);
    insights.push("This result assumes the torque value applies at the stated RPM. It is a calculation, not a dynamometer measurement.");
  } else {
    insights.push("Run an engine calculation or upload a CSV dataset to generate observations.");
    insights.push("TorqueIQ currently provides rule-based observations. A trained AI model is not connected yet.");
  }
  return insights;
});

onMounted(() => {
  try { isDark.value = localStorage.getItem("torqueiq-theme") === "dark"; } catch {}
  checkApi();
});

function toggleTheme() {
  isDark.value = !isDark.value;
  try { localStorage.setItem("torqueiq-theme", isDark.value ? "dark" : "light"); } catch {}
}
function navigate(name) {
  activeTab.value = name;
  mobileMenu.value = false;
}
function selectSearchResult(name) {
  if (name) navigate(name);
  search.value = "";
}

async function checkApi() {
  apiStatus.value = "checking";
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) throw new Error("API unavailable");
    apiStatus.value = "online";
  } catch {
    apiStatus.value = "offline";
  }
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

async function calculateEngine() {
  calculationError.value = "";
  calculationResult.value = null;
  const torque = Number(torqueInput.value);
  const rpm = Number(rpmInput.value);
  if (!Number.isFinite(torque) || torque <= 0 || torque > 10000) {
    calculationError.value = "Enter torque greater than 0 and no more than 10,000 Nm.";
    return;
  }
  if (!Number.isInteger(rpm) || rpm <= 0 || rpm > 30000) {
    calculationError.value = "Enter a whole-number RPM between 1 and 30,000.";
    return;
  }
  isCalculating.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/engine/calculate`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ torque_nm: torque, rpm })
    });
    calculationResult.value = await readResponse(response);
  } catch (error) {
    calculationError.value = `${error.message}. Check that the TorqueIQ backend is running at ${API_BASE_URL}.`;
  } finally { isCalculating.value = false; }
}

async function generateCurve() {
  curveError.value = "";
  curveResult.value = null;
  const torque = Number(torqueInput.value);
  const start = Number(curveStartRpm.value);
  const end = Number(curveEndRpm.value);
  const step = Number(curveStep.value);
  if (!Number.isFinite(torque) || torque <= 0 || torque > 10000) {
    curveError.value = "Enter a valid torque between 0 and 10,000 Nm."; return;
  }
  if (![start, end, step].every(Number.isInteger) || start <= 0 || end < start || end > 30000 || step <= 0 || Math.floor((end-start)/step) > 1000) {
    curveError.value = "Check the RPM range and interval. Use whole numbers and no more than 1,000 intervals."; return;
  }
  isLoadingCurve.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/engine/curve`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ torque_nm: torque, start_rpm: start, end_rpm: end, step })
    });
    curveResult.value = await readResponse(response);
  } catch (error) {
    curveError.value = `${error.message}. Check the backend connection.`;
  } finally { isLoadingCurve.value = false; }
}

function onDatasetSelected(event) {
  selectedDataset.value = event.target.files?.[0] || null;
  datasetResult.value = null;
  datasetError.value = "";
}

async function uploadDataset() {
  datasetError.value = "";
  datasetResult.value = null;
  if (!selectedDataset.value) { datasetError.value = "Choose a CSV file first."; return; }
  if (!selectedDataset.value.name.toLowerCase().endsWith(".csv")) { datasetError.value = "Only CSV files are supported."; return; }
  if (selectedDataset.value.size > 10 * 1024 * 1024) { datasetError.value = "Maximum file size is 10 MB."; return; }
  const formData = new FormData();
  formData.append("file", selectedDataset.value);
  isUploadingDataset.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/datasets/upload`, { method: "POST", body: formData });
    datasetResult.value = await readResponse(response);
  } catch (error) {
    datasetError.value = `${error.message}. Ensure the dataset upload API is running.`;
  } finally { isUploadingDataset.value = false; }
}

function onDiagnosticFileSelected(event) {
  diagnosticFile.value = event.target.files?.[0] || null;
  diagnosticResult.value = null;
  diagnosticError.value = "";
}

async function runDiagnostics() {
  diagnosticError.value = "";
  diagnosticResult.value = null;

  if (!diagnosticFile.value) {
    diagnosticError.value = "Choose a CSV file first.";
    return;
  }

  if (!diagnosticFile.value.name.toLowerCase().endsWith(".csv")) {
    diagnosticError.value = "Only CSV files are supported.";
    return;
  }

  if (diagnosticFile.value.size > 10 * 1024 * 1024) {
    diagnosticError.value = "Maximum file size is 10 MB.";
    return;
  }

  const formData = new FormData();
  formData.append("file", diagnosticFile.value);
  isDiagnosing.value = true;

  try {
    const response = await fetch(`${API_BASE_URL}/api/datasets/diagnose`, {
      method: "POST",
      body: formData
    });
    const result = await readResponse(response);
    diagnosticResult.value = result.diagnostics;
  } catch (error) {
    diagnosticError.value = `${error.message}. Check that the backend is running and the diagnostics endpoint is available.`;
  } finally {
    isDiagnosing.value = false;
  }
}

function onComparisonFileSelected(event, engine) {
  const file = event.target.files?.[0] || null;
  if (engine === "a") compareAFile.value = file;
  else compareBFile.value = file;
  compareResult.value = null;
  compareError.value = "";
}

async function compareEngineDatasets() {
  compareError.value = "";
  compareResult.value = null;
  if (!compareAFile.value || !compareBFile.value) {
    compareError.value = "Choose a CSV file for both Engine A and Engine B.";
    return;
  }
  for (const file of [compareAFile.value, compareBFile.value]) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      compareError.value = "Both files must be CSV files.";
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      compareError.value = "Each CSV must be no larger than 10 MB.";
      return;
    }
  }
  const formData = new FormData();
  formData.append("engine_a", compareAFile.value);
  formData.append("engine_b", compareBFile.value);
  isComparing.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/datasets/compare`, {
      method: "POST",
      body: formData
    });
    compareResult.value = await readResponse(response);
  } catch (error) {
    compareError.value = `${error.message}. Check that the backend is running.`;
  } finally {
    isComparing.value = false;
  }
}

function downloadComparisonCsv() {
  if (!compareResult.value) return;
  const rows = [
    ...compareResult.value.engine_a.data.map(row => ({ engine: "Engine A", ...row })),
    ...compareResult.value.engine_b.data.map(row => ({ engine: "Engine B", ...row }))
  ];
  const headers = ["engine", "rpm", "torque_nm", "power_kw"];
  const csv = [headers.join(","), ...rows.map(row => headers.map(key => row[key] ?? "").join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "torqueiq-engine-comparison.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function downloadCsv() {
  let rows = [];
  let filename = "torqueiq-report.csv";
  if (datasetRows.value.length) {
    rows = datasetRows.value;
    filename = "torqueiq-dataset-report.csv";
  } else if (curveResult.value?.curve?.length) {
    rows = curveResult.value.curve;
    filename = "torqueiq-performance-curve.csv";
  } else if (calculationResult.value) {
    rows = [calculationResult.value];
    filename = "torqueiq-calculation-report.csv";
  }
  if (!rows.length) return;
  const headers = [...new Set(rows.flatMap(row => Object.keys(row)))];
  const csv = [headers.join(","), ...rows.map(row => headers.map(key => {
    const value = row[key] ?? "";
    return `"${String(value).replaceAll('"', '""')}"`;
  }).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = filename; link.click();
  URL.revokeObjectURL(url);
}

function downloadSampleCsv() {
  const sample = "rpm,torque_nm\n1000,120\n1500,145\n2000,165\n2500,180\n3000,190\n3500,185\n4000,175\n";
  const blob = new Blob([sample], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = "torqueiq-sample-engine-data.csv"; link.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="app" :class="{ 'dark-mode': isDark }">

    <!-- MOBILE OVERLAY -->
    <div
      v-if="mobileMenu"
      class="mobile-overlay"
      @click="mobileMenu = false"
    ></div>

    <!-- SIDEBAR -->
    <aside
      class="sidebar"
      :class="{ 'sidebar-open': mobileMenu }"
    >

      <div class="brand">
        <div class="brand-symbol">TQ</div>

        <div class="brand-copy">
          <h2>TorqueIQ</h2>
          <span>ENGINEERING SYSTEMS</span>
        </div>

        <button
          class="close-menu"
          @click="mobileMenu = false"
        >
          <X :size="19"/>
        </button>
      </div>

      <div class="workspace">
        <span class="workspace-label">WORKSPACE</span>
        <strong>Engine Development</strong>
        <span class="workspace-sub">
          Personal engineering lab
        </span>
      </div>

      <div class="nav-heading">ANALYSIS</div>

      <nav>
        <button
          v-for="item in navigation"
          :key="item.name"
          class="nav-item"
          :class="{ active: activeTab === item.name }"
          @click="navigate(item.name)"
        >
          <component :is="item.icon" :size="18"/>
          <span>{{ item.name }}</span>
        </button>
      </nav>

      <div class="sidebar-bottom">

        <div class="system-info">
          <span class="system-indicator"></span>
          LOCAL WORKSPACE
        </div>

        <button
          class="nav-item settings"
          @click="navigate('Settings')"
        >
          <Settings :size="18"/>
          Settings
        </button>

        <div class="sidebar-version">
          TORQUEIQ
          <span>VERSION 1.0</span>
        </div>

      </div>
    </aside>

    <!-- MAIN CONTENT -->
    <main class="main">

      <!-- TOP NAVIGATION -->
      <header class="topbar">

        <div class="topbar-left">

          <button
            class="menu-button"
            @click="mobileMenu = true"
          >
            <Menu :size="21"/>
          </button>

          <div class="breadcrumb">
            ENGINEERING /
            <strong>{{ activeTab.toUpperCase() }}</strong>
          </div>

        </div>

        <div class="topbar-right">

          <!-- SEARCH -->
          <div class="search-box">
            <Search :size="16"/>

            <input
              v-model="search"
              placeholder="Search workspace..."
              list="workspace-options"
            />

            <datalist id="workspace-options">
              <option
                v-for="item in filteredNavigation"
                :key="item.name"
                :value="item.name"
              />
            </datalist>

            <button
              v-if="search"
              class="search-go"
              @click="selectSearchResult(filteredNavigation[0]?.name)"
              :disabled="!filteredNavigation.length"
            >
              Go
            </button>
          </div>

          <!-- THEME TOGGLE -->
          <button
            class="theme-toggle"
            @click="toggleTheme"
            :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
          >
            <Sun v-if="isDark" :size="17"/>
            <Moon v-else :size="17"/>

            <span>{{ isDark ? "Dark" : "Light" }}</span>
          </button>

          <!-- NOTIFICATIONS -->
          <button
            class="notification"
            title="Notifications"
          >
            <Bell :size="18"/>
          </button>

          <!-- PROFILE -->
          <div class="user-profile">

            <div class="user-avatar">TQ</div>

            <div class="user-name">
              <strong>Engineer</strong>
              <span>Personal account</span>
            </div>

            <ChevronDown :size="15"/>

          </div>

        </div>
      </header>

      <!-- PAGE CONTENT -->
      <div class="content">

        <!-- OVERVIEW -->
        <section v-if="activeTab === 'Overview'">

          <!-- PAGE TITLE -->
          <div class="page-heading">

            <div>
              <div class="eyebrow">
                ENGINE PERFORMANCE / OVERVIEW
              </div>

              <h1>Engineering overview</h1>

              <p>
                Monitor engine characteristics,
                performance and analysis.
              </p>
            </div>

            <div class="date-label">
              <Clock3 :size="15"/>
              DEVELOPMENT WORKSPACE
            </div>

          </div>

          <!-- INTRO BANNER -->
          <section class="intro-panel">

            <div class="intro-text">

              <span class="intro-label">
                AUTOMOTIVE PERFORMANCE ANALYSIS
              </span>

              <h2>
                Understand the machine.<br/>
                Measure its performance.
              </h2>

              <p>
                A technical workspace for engine calculations,
                performance comparison and intelligent
                engineering analysis.
              </p>

              <button
                class="primary-button"
                @click="navigate('Engine Calculator')"
              >
                Open engine calculator
                <ArrowUpRight :size="17"/>
              </button>

            </div>

            <div class="intro-graphic">

              <div class="instrument">

                <span class="instrument-caption">
                  ENGINE SPEED
                </span>

                <strong>3000</strong>

                <span class="instrument-unit">
                  REV / MIN
                </span>

                <div class="instrument-line"></div>

                <span class="instrument-footer">
                  SAMPLE OPERATING POINT
                </span>

              </div>

            </div>

          </section>

          <!-- PERFORMANCE METRICS -->
          <div class="section-title">

            <div>
              <h2>Performance indicators</h2>
              <p>
                Current illustrative engine configuration
              </p>
            </div>

            <span class="data-label">
              SAMPLE DATA
            </span>

          </div>

          <div class="metrics">

            <article
              class="metric-card"
              v-for="item in metrics"
              :key="item.label"
            >

              <div class="metric-header">
                <span>{{ item.label }}</span>
                <component :is="item.icon" :size="19"/>
              </div>

              <div class="metric-number">
                {{ item.value }}
                <small>{{ item.unit }}</small>
              </div>

              <div class="metric-detail">
                <span class="metric-dot"></span>
                {{ item.detail }}
              </div>

            </article>

          </div>

          <!-- PERFORMANCE GRAPH -->
          <div class="section-title chart-title">

            <div>
              <h2>Engine performance characteristics</h2>
              <p>
                Illustrative torque and power curves across RPM.
              </p>
            </div>

            <button
              class="outline-button"
              @click="navigate('Engine Calculator')"
            >
              View analysis
              <ArrowUpRight :size="15"/>
            </button>

          </div>

          <div class="chart-card">

            <div class="chart-top">

              <div>
                <strong>Performance curve</strong>
                <span>ENGINE / SAMPLE CONFIGURATION A</span>
              </div>

              <div class="legend">
                <span>
                  <i class="torque-dot"></i>
                  Torque (Nm)
                </span>

                <span>
                  <i class="power-dot"></i>
                  Power (kW)
                </span>
              </div>

            </div>

            <div class="chart-area">

              <svg
                viewBox="0 0 590 225"
                preserveAspectRatio="none"
              >

                <defs>
                  <pattern
                    id="chartGrid"
                    width="49"
                    height="38"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M 49 0 L 0 0 0 38"
                      fill="none"
                      stroke="var(--chart-grid, #e7e5e4)"
                      stroke-width="1"
                    />
                  </pattern>
                </defs>

                <rect
                  x="45"
                  y="30"
                  width="490"
                  height="160"
                  fill="url(#chartGrid)"
                />

                <line
                  x1="45"
                  y1="190"
                  x2="535"
                  y2="190"
                  stroke="var(--chart-axis, #a8a29e)"
                />

                <polyline
                  :points="points(sampleTorque, 200)"
                  fill="none"
                  stroke="#c16b42"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />

                <polyline
                  :points="points(samplePower, 100)"
                  fill="none"
                  stroke="#78816f"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />

                <text x="45" y="212" fill="var(--chart-text, #78716c)" font-size="10">
                  1000
                </text>

                <text x="190" y="212" fill="var(--chart-text, #78716c)" font-size="10">
                  2500
                </text>

                <text x="337" y="212" fill="var(--chart-text, #78716c)" font-size="10">
                  4000
                </text>

                <text x="485" y="212" fill="var(--chart-text, #78716c)" font-size="10">
                  5500
                </text>

                <text x="45" y="20" fill="var(--chart-text, #78716c)" font-size="10">
                  OUTPUT
                </text>

              </svg>

            </div>

            <div class="chart-foot">
              <span>ENGINE SPEED (RPM)</span>
              <span>
                Illustrative data — not dynamometer measurements
              </span>
            </div>

          </div>

          <!-- BOTTOM MODULES -->
          <div class="bottom-grid">

            <div class="activity-card">

              <div class="section-title compact">
                <div>
                  <h2>Engineering modules</h2>
                  <p>Tools available in the workspace</p>
                </div>
              </div>

              <button
                class="module-row"
                @click="navigate('Engine Calculator')"
              >
                <div class="module-icon">
                  <Gauge :size="20"/>
                </div>

                <div>
                  <strong>Engine calculator</strong>
                  <span>Power and torque calculations</span>
                </div>

                <ArrowUpRight :size="17"/>
              </button>

              <button
                class="module-row"
                @click="navigate('Engine Comparison')"
              >
                <div class="module-icon">
                  <GitCompare :size="20"/>
                </div>

                <div>
                  <strong>Engine comparison</strong>
                  <span>Evaluate engine configurations</span>
                </div>

                <ArrowUpRight :size="17"/>
              </button>

              <button
                class="module-row"
                @click="navigate('Dataset Manager')"
              >
                <div class="module-icon">
                  <Database :size="20"/>
                </div>

                <div>
                  <strong>Dataset manager</strong>
                  <span>Import and inspect measurements</span>
                </div>

                <ArrowUpRight :size="17"/>
              </button>

            </div>

            <div class="analysis-card">

              <div class="analysis-icon">
                <BrainCircuit :size="23"/>
              </div>

              <span class="eyebrow">
                INTELLIGENCE MODULE
              </span>

              <h2>AI engineering analyst</h2>

              <p>
                Analyse performance measurements and receive
                AI-assisted engineering interpretations.
              </p>

              <div class="planned-status">
                <span></span>
                UNDER DEVELOPMENT
              </div>

              <button
                class="outline-button"
                @click="navigate('AI Analyst')"
              >
                Explore module
                <ArrowUpRight :size="15"/>
              </button>

            </div>

          </div>

        </section>

        <!-- ENGINE CALCULATOR -->
        <section
          v-else-if="activeTab === 'Engine Calculator'"
          class="module-page"
        >
          <div class="eyebrow">
            TORQUEIQ / PERFORMANCE CALCULATOR
          </div>

          <h1>Engine performance calculator</h1>
          <p>Calculate engine power from torque and rotational speed using the TorqueIQ backend.</p>

          <div class="calculator-grid">
            <div class="calculator-card">
              <div class="calculator-card-heading">
                <div>
                  <span class="calculator-kicker">INPUT PARAMETERS</span>
                  <h2>Engine configuration</h2>
                  <p>Enter the operating point you want to analyse.</p>
                </div>
                <div class="calculator-heading-icon"><Gauge :size="21" /></div>
              </div>

              <label for="torque-input">Torque <span>(Nm)</span></label>
              <input
                id="torque-input"
                v-model.number="torqueInput"
                type="number"
                min="0.01"
                max="10000"
                step="0.1"
                placeholder="e.g. 200"
              />

              <label for="rpm-input">Engine speed <span>(RPM)</span></label>
              <input
                id="rpm-input"
                v-model.number="rpmInput"
                type="number"
                min="1"
                max="30000"
                step="1"
                placeholder="e.g. 3000"
              />

              <button
                class="primary-button calculate-button"
                type="button"
                @click="calculateEngine"
                :disabled="isCalculating"
              >
                <Activity v-if="isCalculating" :size="16" />
                {{ isCalculating ? "Calculating..." : "Calculate performance" }}
                <ArrowUpRight v-if="!isCalculating" :size="16" />
              </button>

              <p v-if="calculationError" class="calculation-error" role="alert">
                {{ calculationError }}
              </p>

              <p class="input-note">Accepted range: torque up to 10,000 Nm · speed up to 30,000 RPM.</p>
            </div>

            <div class="calculator-card calculator-results">
              <div class="calculator-card-heading">
                <div>
                  <span class="calculator-kicker">COMPUTED OUTPUT</span>
                  <h2>Performance results</h2>
                  <p>Values returned by your FastAPI engine.</p>
                </div>
                <div class="calculator-heading-icon"><Zap :size="21" /></div>
              </div>

              <div v-if="calculationResult" class="result-list" aria-live="polite">
                <div class="result-row">
                  <span>Input torque</span>
                  <strong>{{ calculationResult.torque_nm }} <small>Nm</small></strong>
                </div>
                <div class="result-row">
                  <span>Engine speed</span>
                  <strong>{{ calculationResult.rpm.toLocaleString() }} <small>RPM</small></strong>
                </div>
                <div class="result-row result-primary">
                  <span>Power output</span>
                  <strong>{{ calculationResult.power_kw }} <small>kW</small></strong>
                </div>
                <div class="result-row result-primary">
                  <span>Horsepower</span>
                  <strong>{{ calculationResult.power_hp }} <small>HP</small></strong>
                </div>
                <div class="result-success"><span></span> Calculation completed successfully</div>
              </div>

              <div v-else class="empty-result">
                <div class="empty-result-icon"><Gauge :size="25" /></div>
                <strong>Your results will appear here</strong>
                <span>Enter torque and RPM, then select Calculate performance.</span>
              </div>
            </div>
          </div>

          <div class="formula-note">
            <div class="formula-note-icon"><Activity :size="18" /></div>
            <div>
              <strong>Engineering note</strong>
              <p>Power is calculated from torque and rotational speed. Results are theoretical values for the supplied operating point, not measured dynamometer data.</p>
            </div>
          </div>

          <section class="curve-panel">
            <div class="curve-heading">
              <div>
                <span class="calculator-kicker">RPM ANALYSIS</span>
                <h2>Dynamic power curve</h2>
                <p>Generate a power curve from your selected torque and RPM range.</p>
              </div>
              <div class="calculator-heading-icon"><Activity :size="21" /></div>
            </div>

            <div class="curve-controls">
              <div>
                <label for="curve-start">Start RPM</label>
                <input id="curve-start" v-model.number="curveStartRpm" type="number" min="1" max="30000" />
              </div>
              <div>
                <label for="curve-end">End RPM</label>
                <input id="curve-end" v-model.number="curveEndRpm" type="number" min="1" max="30000" />
              </div>
              <div>
                <label for="curve-step">RPM interval</label>
                <input id="curve-step" v-model.number="curveStep" type="number" min="1" max="10000" />
              </div>
              <button class="primary-button calculate-button" type="button" @click="generateCurve" :disabled="isLoadingCurve">
                {{ isLoadingCurve ? "Generating..." : "Generate curve" }}
                <ArrowUpRight v-if="!isLoadingCurve" :size="16" />
              </button>
            </div>

            <p v-if="curveError" class="calculation-error" role="alert">{{ curveError }}</p>

            <div v-if="curveResult" class="curve-chart-wrap">
              <div class="curve-chart-meta">
                <span>POWER OUTPUT (kW)</span>
                <span>{{ curveResult.curve.length }} calculated points</span>
              </div>
              <svg class="curve-chart" viewBox="0 0 600 230" role="img" aria-label="Calculated engine power curve across RPM">
                <line v-for="y in [45, 90, 135, 190]" :key="y" x1="48" :y1="y" x2="552" :y2="y" stroke="var(--border)" stroke-dasharray="4 5" />
                <polyline :points="curvePolyline" fill="none" stroke="#c16b42" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
                <text x="48" y="215" fill="var(--text-muted)" font-size="11">{{ curveResult.curve[0].rpm }} RPM</text>
                <text x="552" y="215" fill="var(--text-muted)" font-size="11" text-anchor="end">{{ curveResult.curve[curveResult.curve.length - 1].rpm }} RPM</text>
              </svg>
              <p class="curve-disclaimer">Illustrative constant-torque model. This is not a measured engine dyno curve.</p>
              <div class="curve-table">
                <div v-for="point in curveResult.curve" :key="point.rpm">
                  <span>{{ point.rpm.toLocaleString() }} RPM</span>
                  <strong>{{ point.power_kw }} kW</strong>
                </div>
              </div>
            </div>
            <div v-else class="curve-empty">Set the RPM range and select Generate curve to view the calculated power profile.</div>
          </section>
        </section>

        <!-- ENGINE COMPARISON -->
        <section v-else-if="activeTab === 'Engine Comparison'" class="module-page">
          <div class="eyebrow">TORQUEIQ / COMPARATIVE ANALYSIS</div>
          <h1>Engine comparison</h1>
          <p>Upload two engine measurement CSV files to compare their measured torque and calculated or supplied power profiles.</p>

          <div class="comparison-grid dataset-comparison-grid">
            <article class="calculator-card">
              <span class="calculator-kicker">DATASET A</span>
              <h2>Engine A</h2>
              <p class="comparison-upload-copy">Select your baseline engine CSV.</p>
              <input type="file" accept=".csv,text/csv" @change="onComparisonFileSelected($event, 'a')" />
              <div v-if="compareAFile" class="selected-file"><FileText :size="16" /> {{ compareAFile.name }} · {{ (compareAFile.size / 1024).toFixed(1) }} KB</div>
            </article>
            <article class="calculator-card">
              <span class="calculator-kicker">DATASET B</span>
              <h2>Engine B</h2>
              <p class="comparison-upload-copy">Select the engine you want to compare.</p>
              <input type="file" accept=".csv,text/csv" @change="onComparisonFileSelected($event, 'b')" />
              <div v-if="compareBFile" class="selected-file"><FileText :size="16" /> {{ compareBFile.name }} · {{ (compareBFile.size / 1024).toFixed(1) }} KB</div>
            </article>
          </div>

          <div class="upload-actions comparison-actions">
            <button class="primary-button" type="button" @click="compareEngineDatasets" :disabled="isComparing">
              <GitCompare :size="16" /> {{ isComparing ? 'Comparing datasets...' : 'Compare engines' }}
            </button>
            <button v-if="compareResult" class="outline-button" type="button" @click="downloadComparisonCsv">
              <Download :size="15" /> Export comparison CSV
            </button>
          </div>
          <p v-if="compareError" class="calculation-error" role="alert">{{ compareError }}</p>

          <div v-if="compareResult" class="dataset-results comparison-results">
            <div class="section-title"><div><h2>Comparison summary</h2><p>{{ compareResult.engine_a.metrics.records }} records in Engine A · {{ compareResult.engine_b.metrics.records }} records in Engine B</p></div><span class="data-label">COMPLETE</span></div>
            <div class="metrics dataset-metrics">
              <article class="metric-card"><div class="metric-header">Engine A peak torque</div><div class="metric-number">{{ Number(compareResult.engine_a.metrics.peak_torque_nm).toFixed(2) }}<small>Nm</small></div><p class="comparison-metric-detail">At {{ Number(compareResult.engine_a.metrics.peak_torque_rpm).toLocaleString() }} RPM</p></article>
              <article class="metric-card"><div class="metric-header">Engine B peak torque</div><div class="metric-number">{{ Number(compareResult.engine_b.metrics.peak_torque_nm).toFixed(2) }}<small>Nm</small></div><p class="comparison-metric-detail">At {{ Number(compareResult.engine_b.metrics.peak_torque_rpm).toLocaleString() }} RPM</p></article>
              <article class="metric-card"><div class="metric-header">Engine A peak power</div><div class="metric-number">{{ Number(compareResult.engine_a.metrics.peak_power_kw).toFixed(2) }}<small>kW</small></div><p class="comparison-metric-detail">At {{ Number(compareResult.engine_a.metrics.peak_power_rpm).toLocaleString() }} RPM</p></article>
              <article class="metric-card"><div class="metric-header">Engine B peak power</div><div class="metric-number">{{ Number(compareResult.engine_b.metrics.peak_power_kw).toFixed(2) }}<small>kW</small></div><p class="comparison-metric-detail">At {{ Number(compareResult.engine_b.metrics.peak_power_rpm).toLocaleString() }} RPM</p></article>
            </div>

            <div class="comparison-summary comparison-difference-summary">
              <h2>Relative difference · Engine B vs Engine A</h2>
              <div class="comparison-difference-grid">
                <div><span>Peak torque</span><strong>{{ compareResult.comparison.peak_torque_difference_percent > 0 ? '+' : '' }}{{ compareResult.comparison.peak_torque_difference_percent }}%</strong></div>
                <div><span>Peak power</span><strong>{{ compareResult.comparison.peak_power_difference_percent > 0 ? '+' : '' }}{{ compareResult.comparison.peak_power_difference_percent }}%</strong></div>
              </div>
            </div>

            <section class="comparison-chart-card">
              <div class="section-title"><div><h2>Performance curves</h2><p>Measurements are compared across the available RPM range.</p></div></div>
              <div class="chart-mode-switch">
                <button type="button" :class="{ active: comparisonChartMode === 'torque' }" @click="comparisonChartMode = 'torque'">Torque (Nm)</button>
                <button type="button" :class="{ active: comparisonChartMode === 'power' }" @click="comparisonChartMode = 'power'">Power (kW)</button>
              </div>
              <div class="comparison-legend"><span><i class="legend-a"></i> Engine A</span><span><i class="legend-b"></i> Engine B</span></div>
              <svg class="comparison-chart" viewBox="0 0 600 230" role="img" :aria-label="comparisonChartMode === 'torque' ? 'Torque comparison chart' : 'Power comparison chart'">
                <line x1="45" y1="35" x2="555" y2="35" stroke="var(--border)" />
                <line x1="45" y1="85" x2="555" y2="85" stroke="var(--border)" />
                <line x1="45" y1="135" x2="555" y2="135" stroke="var(--border)" />
                <line x1="45" y1="190" x2="555" y2="190" stroke="var(--border)" />
                <polyline :points="comparisonChartLines.a" fill="none" stroke="#c16b42" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
                <polyline :points="comparisonChartLines.b" fill="none" stroke="#6486a5" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
                <text x="48" y="215" fill="var(--text-muted)" font-size="11">{{ comparisonRows[0]?.rpm }} RPM</text>
                <text x="552" y="215" fill="var(--text-muted)" font-size="11" text-anchor="end">{{ comparisonRows[comparisonRows.length - 1]?.rpm }} RPM</text>
              </svg>
              <p class="curve-disclaimer">Power values are taken from each CSV after processing. If power was absent, TorqueIQ calculated it from torque and RPM. Curves between unmatched RPM samples use linear interpolation for display only.</p>
            </section>

            <div class="comparison-summary">
              <h2>Engineering observations</h2>
              <p>Engine B has {{ compareResult.comparison.peak_torque_difference_percent >= 0 ? 'higher' : 'lower' }} peak torque than Engine A by {{ Math.abs(compareResult.comparison.peak_torque_difference_percent).toFixed(2) }}%, and {{ compareResult.comparison.peak_power_difference_percent >= 0 ? 'higher' : 'lower' }} peak power by {{ Math.abs(compareResult.comparison.peak_power_difference_percent).toFixed(2) }}%.</p>
              <p class="curve-disclaimer">This is a comparison of the supplied datasets. Different test conditions, correction standards, fuel, temperature, and measurement equipment can affect results.</p>
            </div>
          </div>
        </section>

        <!-- DATASET MANAGER -->
        <section v-else-if="activeTab === 'Dataset Manager'" class="module-page">
          <div class="eyebrow">TORQUEIQ / DATA MANAGEMENT</div>
          <h1>Dataset manager</h1>
          <p>Upload a CSV containing <strong>rpm</strong> and <strong>torque_nm</strong> columns. Power is calculated if not supplied.</p>
          <div class="dataset-upload-card">
            <div class="upload-icon"><Upload :size="25" /></div>
            <h2>Import engine measurements</h2>
            <p>CSV format · Maximum 10 MB · Required columns: rpm, torque_nm</p>
            <input type="file" accept=".csv,text/csv" @change="onDatasetSelected" />
            <div v-if="selectedDataset" class="selected-file"><FileText :size="16" /> {{ selectedDataset.name }} · {{ (selectedDataset.size / 1024).toFixed(1) }} KB</div>
            <div class="upload-actions">
              <button class="primary-button" type="button" @click="uploadDataset" :disabled="isUploadingDataset">
                <Upload :size="15" /> {{ isUploadingDataset ? 'Uploading and processing...' : 'Upload and process CSV' }}
              </button>
              <button class="outline-button" type="button" @click="downloadSampleCsv"><Download :size="15" /> Download sample CSV</button>
            </div>
            <p v-if="datasetError" class="calculation-error" role="alert">{{ datasetError }}</p>
          </div>
          <div v-if="datasetResult" class="dataset-results">
            <div class="section-title"><div><h2>Processing summary</h2><p>{{ datasetResult.filename }}</p></div><span class="data-label">PROCESSED</span></div>
            <div class="metrics dataset-metrics">
              <article class="metric-card"><div class="metric-header">Valid records</div><div class="metric-number">{{ datasetResult.records }}</div></article>
              <article class="metric-card"><div class="metric-header">RPM range</div><div class="metric-number metric-small">{{ Number(datasetResult.rpm_min).toLocaleString() }}–{{ Number(datasetResult.rpm_max).toLocaleString() }}</div></article>
              <article class="metric-card"><div class="metric-header">Peak torque</div><div class="metric-number">{{ Number(datasetResult.peak_torque_nm).toFixed(2) }}<small>Nm</small></div></article>
              <article class="metric-card"><div class="metric-header">Peak power</div><div class="metric-number">{{ Number(datasetResult.peak_power_kw).toFixed(2) }}<small>kW</small></div></article>
            </div>
            <div class="table-wrap">
              <table class="data-table">
                <thead><tr><th v-for="key in Object.keys(datasetRows[0] || {})" :key="key">{{ key }}</th></tr></thead>
                <tbody><tr v-for="(row, index) in datasetRows.slice(0, 100)" :key="index"><td v-for="key in Object.keys(datasetRows[0] || {})" :key="key">{{ typeof row[key] === 'number' ? row[key].toFixed(3) : row[key] }}</td></tr></tbody>
              </table>
              <p class="table-note">Showing up to 100 rows in the preview. The exported report includes all processed records.</p>
            </div>
            <button class="primary-button" type="button" @click="downloadCsv"><Download :size="15" /> Export processed dataset</button>
          </div>
          <div v-else class="curve-empty">No dataset uploaded in this session yet. Download the sample CSV to see the expected format.</div>
        </section>

        <!-- AI ANALYST / ENGINE DIAGNOSTICS -->
        <section v-else-if="activeTab === 'AI Analyst'" class="module-page">
          <div class="eyebrow">TORQUEIQ / ENGINEERING INTELLIGENCE</div>
          <h1>Engine diagnostics</h1>
          <p>Upload engine measurements to identify unusual data patterns and receive explainable engineering observations.</p>

          <div class="dataset-upload-card diagnostic-upload-card">
            <div class="upload-icon"><BrainCircuit :size="25" /></div>
            <h2>Run engine diagnostics</h2>
            <p>CSV format · Maximum 10 MB · Required columns: rpm, torque_nm</p>
            <input type="file" accept=".csv,text/csv" @change="onDiagnosticFileSelected" />
            <div v-if="diagnosticFile" class="selected-file"><FileText :size="16" /> {{ diagnosticFile.name }} · {{ (diagnosticFile.size / 1024).toFixed(1) }} KB</div>
            <div class="upload-actions">
              <button class="primary-button" type="button" @click="runDiagnostics" :disabled="isDiagnosing">
                <Activity :size="15" /> {{ isDiagnosing ? 'Analysing engine data...' : 'Run diagnostics' }}
              </button>
            </div>
            <p v-if="diagnosticError" class="calculation-error" role="alert">{{ diagnosticError }}</p>
          </div>

          <div v-if="diagnosticResult" class="diagnostic-results" aria-live="polite">
            <div class="section-title">
              <div><h2>Diagnostic summary</h2><p>{{ diagnosticResult.records_analysed }} records analysed · {{ diagnosticResult.analysis_type }}</p></div>
              <span class="data-label">ANALYSIS COMPLETE</span>
            </div>

            <div class="metrics dataset-metrics">
              <article class="metric-card">
                <div class="metric-header">Peak torque</div>
                <div class="metric-number">{{ Number(diagnosticResult.peak_torque_nm).toFixed(2) }}<small>Nm</small></div>
                <p class="comparison-metric-detail">At {{ Number(diagnosticResult.peak_torque_rpm).toLocaleString() }} RPM</p>
              </article>
              <article class="metric-card">
                <div class="metric-header">Peak power</div>
                <div class="metric-number">{{ Number(diagnosticResult.peak_power_kw).toFixed(2) }}<small>kW</small></div>
                <p class="comparison-metric-detail">At {{ Number(diagnosticResult.peak_power_rpm).toLocaleString() }} RPM</p>
              </article>
              <article class="metric-card">
                <div class="metric-header">Torque drop</div>
                <div class="metric-number">{{ Number(diagnosticResult.torque_drop_percent).toFixed(2) }}<small>%</small></div>
                <p class="comparison-metric-detail">Peak to highest recorded RPM</p>
              </article>
              <article class="metric-card">
                <div class="metric-header">Findings</div>
                <div class="metric-number">{{ diagnosticResult.findings_count }}</div>
                <p class="comparison-metric-detail">Patterns flagged by current rules</p>
              </article>
            </div>

            <div class="diagnostic-findings">
              <h2>Diagnostic findings</h2>
              <article v-for="(finding, index) in diagnosticResult.findings" :key="`${finding.code}-${index}`" class="diagnostic-finding" :class="`severity-${finding.severity}`">
                <div class="diagnostic-finding-top">
                  <strong>{{ finding.title }}</strong>
                  <span class="diagnostic-severity">{{ finding.severity }}</span>
                </div>
                <p>{{ finding.description }}</p>
                <div class="diagnostic-recommendation"><strong>Suggested next step:</strong> {{ finding.recommendation }}</div>
                <span class="diagnostic-code">{{ finding.code }}</span>
              </article>
            </div>

            <div class="analysis-disclaimer"><AlertCircle :size="16" /> {{ diagnosticResult.limitations }} These rules flag data patterns; they do not confirm mechanical faults or replace qualified inspection.</div>
          </div>

          <div class="analysis-report-card">
            <div class="analysis-report-heading"><BrainCircuit :size="24" /><div><strong>Session observations</strong><span>Based on your latest calculation or dataset upload</span></div></div>
            <ul><li v-for="(insight, index) in aiInsights" :key="index">{{ insight }}</li></ul>
            <div class="analysis-disclaimer"><AlertCircle :size="16" /> TorqueIQ currently uses explainable rules, not a trained machine-learning model or generative AI system.</div>
          </div>
        </section>

        <!-- REPORTS -->
        <section v-else-if="activeTab === 'Reports'" class="module-page">
          <div class="eyebrow">TORQUEIQ / REPORT EXPORT</div>
          <h1>Reports</h1>
          <p>Export the latest available calculation, curve or processed dataset as CSV.</p>
          <div class="report-card">
            <FileText :size="30" />
            <h2>Engineering data export</h2>
            <p v-if="datasetRows.length">Latest report: {{ datasetRows.length }} processed dataset records.</p>
            <p v-else-if="curveResult?.curve?.length">Latest report: {{ curveResult.curve.length }} performance-curve points.</p>
            <p v-else-if="calculationResult">Latest report: one engine calculation.</p>
            <p v-else>No report data available yet. Run a calculation or upload a dataset first.</p>
            <button class="primary-button" type="button" @click="downloadCsv" :disabled="!datasetRows.length && !curveResult?.curve?.length && !calculationResult"><Download :size="16" /> Download CSV report</button>
          </div>
        </section>

        <!-- SETTINGS -->
        <section v-else class="module-page">
          <div class="eyebrow">TORQUEIQ / PREFERENCES</div>
          <h1>Settings</h1>
          <p>Local application and backend connection status.</p>
          <div class="settings-card">
            <div class="settings-row"><div><strong>Appearance</strong><span>Choose the workspace colour theme.</span></div><button class="outline-button" @click="toggleTheme"><Sun v-if="isDark" :size="16" /><Moon v-else :size="16" /> Switch to {{ isDark ? 'light' : 'dark' }} mode</button></div>
            <div class="settings-row"><div><strong>Backend API</strong><span>{{ API_BASE_URL }}</span></div><span class="api-status" :class="apiStatus"><i></i>{{ apiStatus === 'online' ? 'Connected' : apiStatus === 'checking' ? 'Checking...' : 'Offline' }}</span></div>
            <div class="settings-row"><div><strong>Connection test</strong><span>Check whether the FastAPI service is responding.</span></div><button class="outline-button" @click="checkApi"><RefreshCw :size="15" /> Test connection</button></div>
          </div>
        </section>

        <footer>
          <span>TORQUEIQ © 2026</span>
          <span>ENGINEERING PERFORMANCE ANALYSIS</span>
          <span>BUILD 1.0.0</span>
        </footer>

      </div>
    </main>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  font-family: 'DM Sans', sans-serif;
  font-synthesis: none;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
}

button, input {
  font: inherit;
}

button {
  cursor: pointer;
}

/* =================================
   LIGHT THEME
================================= */

.app {
  min-height: 100vh;
  background: #eeede8;
  color: #292d2e;

  --page-bg: #eeede8;
  --surface: #f9f8f4;
  --surface-secondary: #f6f5f0;
  --text-main: #292d2e;
  --text-muted: #777c79;
  --border: #dddbd3;
  --accent: #b96743;
  --chart-grid: #e7e5e4;
  --chart-axis: #a8a29e;
  --chart-text: #78716c;

  transition:
    background-color .25s ease,
    color .25s ease;
}

/* =================================
   DARK THEME
================================= */

.app.dark-mode {
  background: #171a1c;
  color: #e5e4df;

  --page-bg: #171a1c;
  --surface: #23292b;
  --surface-secondary: #202426;
  --text-main: #eeede8;
  --text-muted: #a3aaa7;
  --border: #3b4244;
  --accent: #d58a64;
  --chart-grid: #34393b;
  --chart-axis: #626a6b;
  --chart-text: #a3aaa7;
}

/* =================================
   SIDEBAR
================================= */

.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 20;
  width: 245px;
  background: #252b30;
  color: #e9e8e2;
  padding: 29px 20px;
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 48px;
}

.brand-symbol {
  height: 39px;
  width: 39px;
  display: grid;
  place-items: center;
  background: #c16b42;
  color: white;
  font-family: 'Space Grotesk';
  font-size: 14px;
  font-weight: 700;
  border-radius: 5px;
}

.brand h2 {
  font-family: 'Space Grotesk';
  font-size: 20px;
  margin: 0;
  font-weight: 700;
  letter-spacing: -.7px;
}

.brand-copy span {
  display: block;
  font-size: 8px;
  color: #a8adae;
  letter-spacing: 1.4px;
  margin-top: 4px;
}

.workspace {
  padding: 15px;
  background: #30383d;
  border: 1px solid #414a50;
  border-radius: 5px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 38px;
}

.workspace-label, .nav-heading {
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #a5aaa9;
  font-weight: 700;
}

.workspace strong {
  font-size: 12px;
}

.workspace-sub {
  font-size: 10px;
  color: #a5aaa9;
}

.nav-heading {
  margin: 0 0 12px 10px;
}

.sidebar nav {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 11px;
  border: 0;
  border-radius: 4px;
  color: #c0c5c3;
  background: transparent;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  transition: .18s;
}

.nav-item:hover {
  background: #343d42;
  color: white;
}

.nav-item.active {
  color: #fff;
  background: #414a50;
  border-left: 3px solid #c16b42;
  padding-left: 8px;
}

.sidebar-bottom {
  margin-top: auto;
}

.system-info {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 8px;
  color: #adb4b2;
  letter-spacing: 1px;
  border-bottom: 1px solid #42494d;
  padding: 15px 2px;
  margin-bottom: 13px;
}

.system-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #82927d;
}

.settings {
  margin-bottom: 15px;
}

.sidebar-version {
  border-top: 1px solid #42494d;
  padding-top: 18px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
  display: flex;
  justify-content: space-between;
}

.sidebar-version span {
  color: #929b9c;
  font-weight: 400;
}

.close-menu, .menu-button, .mobile-overlay {
  display: none;
}

/* =================================
   MAIN
================================= */

.main {
  margin-left: 245px;
  min-height: 100vh;
  background: var(--page-bg);
  transition: background .25s ease;
}

.topbar {
  height: 70px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 38px;
  transition: background .25s, border .25s;
}

.breadcrumb {
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.2px;
}

.breadcrumb strong {
  color: var(--text-main);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 17px;
}

/* SEARCH */

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text-muted);
  background: var(--surface);
}

.search-box input {
  border: 0;
  outline: none;
  width: 130px;
  font-size: 10px;
  background: transparent;
  color: var(--text-main);
}

.search-box input::placeholder {
  color: var(--text-muted);
}

.search-go {
  border: 0;
  background: var(--accent);
  color: white;
  padding: 4px 7px;
  border-radius: 3px;
  font-size: 9px;
}

.search-go:disabled {
  opacity: .5;
  cursor: not-allowed;
}

/* THEME BUTTON */

.theme-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--border);
  background: var(--surface-secondary);
  color: var(--text-main);
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  transition: background .25s, color .25s, border .25s;
}

.theme-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.notification {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-main);
  padding: 8px;
  border-radius: 4px;
}

.notification:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--text-main);
}

.user-avatar {
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  background: #414a50;
  color: white;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
}

.user-name {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.user-name strong {
  font-size: 10px;
}

.user-name span {
  font-size: 9px;
  color: var(--text-muted);
}

/* =================================
   CONTENT
================================= */

.content {
  max-width: 1500px;
  margin: 0 auto;
  padding: 34px 38px;
}

.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 25px;
}

.eyebrow {
  color: #a15c3e;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 1.5px;
}

.dark-mode .eyebrow {
  color: #d58a64;
}

.page-heading h1, .module-page h1 {
  font-family: 'Space Grotesk';
  font-size: 30px;
  letter-spacing: -1px;
  font-weight: 700;
  margin: 9px 0 5px;
  color: var(--text-main);
}

.page-heading p, .module-page > p {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0;
}

.date-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 10px 12px;
  border-radius: 4px;
  background: var(--surface-secondary);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: .8px;
}

/* INTRO */

.intro-panel {
  min-height: 235px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px 38px;
  background: #30383d;
  color: white;
  border-radius: 5px;
  position: relative;
  overflow: hidden;
}

.intro-text {
  max-width: 540px;
  position: relative;
  z-index: 2;
}

.intro-label {
  font-size: 8px;
  letter-spacing: 1.8px;
  font-weight: 800;
  color: #d7a287;
}

.intro-text h2 {
  font-family: 'Space Grotesk';
  font-size: clamp(25px, 3vw, 36px);
  line-height: 1.2;
  letter-spacing: -1.2px;
  margin: 15px 0 10px;
  font-weight: 700;
}

.intro-text p {
  font-size: 11px;
  line-height: 1.8;
  color: #c1c6c3;
  max-width: 450px;
}

.primary-button {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 12px 15px;
  border: 0;
  border-radius: 4px;
  color: white;
  background: #b96743;
  font-size: 10px;
  font-weight: 700;
  margin-top: 12px;
  transition: .2s;
}

.primary-button:hover {
  background: #a95837;
}

.intro-graphic {
  width: 260px;
  height: 180px;
  display: grid;
  place-items: center;
  background: #394248;
  border: 1px solid #566066;
  border-radius: 4px;
  margin-left: 20px;
}

.instrument {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.instrument-caption, .instrument-footer {
  font-size: 8px;
  color: #adb6b5;
  letter-spacing: 1.5px;
}

.instrument strong {
  font-family: 'Space Grotesk';
  font-size: 48px;
  letter-spacing: -2px;
  margin: 8px 0 0;
}

.instrument-unit {
  font-size: 9px;
  color: #d6a083;
  font-weight: 700;
  letter-spacing: 1px;
}

.instrument-line {
  width: 120px;
  height: 3px;
  background: #c16b42;
  margin: 14px 0;
}

/* METRICS */

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin: 32px 0 15px;
}

.section-title h2 {
  font-family: 'Space Grotesk';
  font-size: 17px;
  font-weight: 700;
  margin: 0 0 5px;
  color: var(--text-main);
}

.section-title p {
  font-size: 10px;
  color: var(--text-muted);
  margin: 0;
}

.data-label {
  color: #a15c3e;
  background: #f1e7df;
  border: 1px solid #e2cbbd;
  border-radius: 3px;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 1px;
  padding: 7px 9px;
}

.dark-mode .data-label {
  color: #e0a17f;
  background: #3c302b;
  border-color: #604638;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0,1fr));
  gap: 12px;
}

.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 18px;
  min-width: 0;
  transition: background .25s, border .25s;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 600;
}

.metric-header svg {
  color: var(--accent);
}

.metric-number {
  font-family: 'Space Grotesk';
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -1px;
  margin: 19px 0 13px;
  color: var(--text-main);
}

.metric-number small {
  font-family: 'DM Sans';
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-left: 5px;
}

.metric-detail {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-muted);
  font-size: 9px;
}

.metric-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #87937c;
}

/* CHART */

.chart-title {
  margin-top: 34px;
}

.outline-button {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  border: 1px solid var(--border);
  background: var(--surface-secondary);
  color: var(--text-main);
  padding: 9px 12px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
}

.outline-button:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 19px 20px 13px;
  transition: background .25s, border .25s;
}

.chart-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-top > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.chart-top strong {
  font-size: 11px;
  color: var(--text-main);
}

.chart-top span {
  font-size: 8px;
  color: var(--text-muted);
  letter-spacing: .7px;
}

.legend {
  display: flex;
  gap: 15px;
}

.legend span {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 9px;
}

.legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.torque-dot { background: #c16b42; }
.power-dot { background: #78816f; }

.chart-area {
  height: 220px;
  margin-top: 14px;
}

.chart-area svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.chart-foot {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--border);
  padding-top: 12px;
  font-size: 8px;
  color: var(--text-muted);
}

/* BOTTOM */

.bottom-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 13px;
  margin-top: 17px;
}

.activity-card, .analysis-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 20px;
  transition: background .25s, border .25s;
}

.compact {
  margin: 0 0 10px;
}

.module-row {
  display: flex;
  width: 100%;
  align-items: center;
  text-align: left;
  gap: 12px;
  padding: 12px 5px;
  border: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text-main);
}

.module-row:hover {
  background: var(--surface-secondary);
}

.module-icon {
  width: 36px;
  height: 36px;
  background: #eeeae2;
  color: #a15c3e;
  display: grid;
  place-items: center;
  border-radius: 4px;
}

.dark-mode .module-icon {
  background: #373b39;
  color: #d58a64;
}

.module-row > div:nth-child(2) {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.module-row strong {
  font-size: 10px;
}

.module-row span {
  font-size: 9px;
  color: var(--text-muted);
}

.module-row > svg {
  margin-left: auto;
  color: var(--text-muted);
}

.analysis-card {
  background: #30383d;
  color: white;
}

.analysis-icon {
  color: #d69a79;
  margin-bottom: 14px;
}

.analysis-card .eyebrow {
  color: #d69a79;
}

.analysis-card h2 {
  font-family: 'Space Grotesk';
  font-size: 19px;
  margin: 10px 0;
}

.analysis-card p {
  color: #c2c7c3;
  font-size: 10px;
  line-height: 1.8;
}

.planned-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 8px;
  color: #d7a287;
  letter-spacing: 1px;
  margin: 15px 0;
  font-weight: 700;
}

.planned-status span {
  height: 6px;
  width: 6px;
  border-radius: 50%;
  background: #c16b42;
}

.analysis-card .outline-button {
  background: transparent;
  border-color: #687176;
  color: white;
}

/* OTHER MODULES */

.module-page {
  min-height: 550px;
  padding-top: 25px;
}

.module-placeholder {
  margin-top: 30px;
  min-height: 260px;
  border: 1px dashed var(--border);
  background: var(--surface);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  border-radius: 5px;
}

.module-placeholder > svg {
  color: var(--accent);
}

.module-placeholder h2 {
  font-family: 'Space Grotesk';
  font-size: 17px;
}

.module-placeholder p {
  font-size: 10px;
  color: var(--text-muted);
}

/* FOOTER */

footer {
  border-top: 1px solid var(--border);
  padding-top: 17px;
  margin-top: 35px;
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 8px;
  letter-spacing: 1px;
  font-weight: 600;
}

/* =================================
   RESPONSIVE
================================= */

@media(max-width: 1100px) {
  .metrics {
    grid-template-columns: repeat(2,1fr);
  }

  .intro-graphic {
    width: 200px;
  }
}

@media(max-width: 800px) {
  .sidebar {
    left: -260px;
    transition: left .25s;
  }

  .sidebar.sidebar-open {
    left: 0;
  }

  .main {
    margin-left: 0;
  }

  .mobile-overlay {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 19;
    background: rgba(0,0,0,.45);
  }

  .menu-button, .close-menu {
    display: grid;
    place-items: center;
    border: 0;
    background: transparent;
    color: inherit;
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .content {
    padding: 25px 20px;
  }

  .topbar {
    padding: 0 20px;
  }

  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

@media(max-width: 550px) {
  .search-box {
    display: none;
  }

  .user-name, .user-profile > svg {
    display: none;
  }

  .theme-toggle span {
    display: none;
  }

  .theme-toggle {
    padding: 9px;
  }

  .page-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 15px;
  }

  .intro-panel {
    padding: 25px 20px;
  }

  .intro-graphic {
    display: none;
  }

  .metrics {
    gap: 8px;
  }

  .metric-card {
    padding: 12px;
  }

  .metric-number {
    font-size: 23px;
  }

  .chart-top {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .legend {
    flex-wrap: wrap;
  }

  .chart-area {
    height: 180px;
  }

  .chart-foot {
    flex-direction: column;
    gap: 7px;
  }

  footer {
    flex-wrap: wrap;
    gap: 12px;
  }
}


/* =================================
   ENGINE CALCULATOR
================================= */

.calculator-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 28px;
}

.calculator-card {
  min-width: 0;
  padding: 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
}

.calculator-card-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 26px;
}

.calculator-kicker {
  color: var(--accent);
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 1.3px;
}

.calculator-card-heading h2 {
  margin: 7px 0 5px;
  color: var(--text-main);
  font-family: 'Space Grotesk';
  font-size: 19px;
}

.calculator-card-heading p {
  margin: 0;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.6;
}

.calculator-heading-icon, .empty-result-icon, .formula-note-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  color: var(--accent);
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
}

.calculator-card label {
  display: block;
  margin: 19px 0 8px;
  color: var(--text-main);
  font-size: 10px;
  font-weight: 700;
}

.calculator-card label span {
  color: var(--text-muted);
  font-weight: 500;
}

.calculator-card input {
  display: block;
  width: 100%;
  min-height: 43px;
  padding: 11px 12px;
  color: var(--text-main);
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  outline: none;
  font-size: 12px;
}

.calculator-card input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 14%, transparent);
}

.calculate-button {
  margin-top: 24px;
}

.calculate-button:disabled {
  opacity: .65;
  cursor: wait;
}

.input-note {
  margin: 15px 0 0;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 1.6;
}

.result-list {
  display: flex;
  flex-direction: column;
}

.result-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 17px 0;
  border-bottom: 1px solid var(--border);
}

.result-row > span {
  color: var(--text-muted);
  font-size: 11px;
}

.result-row strong {
  color: var(--text-main);
  font-family: 'Space Grotesk';
  font-size: 17px;
  overflow-wrap: anywhere;
}

.result-row strong small {
  color: var(--text-muted);
  font-family: 'DM Sans';
  font-size: 10px;
}

.result-row.result-primary strong {
  color: var(--accent);
  font-size: 21px;
}

.result-success {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 19px;
  color: var(--text-muted);
  font-size: 9px;
}

.result-success span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #82927d;
}

.empty-result {
  min-height: 245px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 11px;
  text-align: center;
  padding: 20px;
}

.empty-result strong {
  color: var(--text-main);
  font-family: 'Space Grotesk';
  font-size: 13px;
}

.empty-result > span {
  max-width: 260px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.7;
}

.calculation-error {
  margin: 13px 0 0;
  padding: 10px 12px;
  color: #b8473d;
  background: rgba(184, 71, 61, .08);
  border: 1px solid rgba(184, 71, 61, .2);
  border-radius: 4px;
  font-size: 10px;
  line-height: 1.5;
}

.formula-note {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  margin-top: 16px;
  padding: 17px;
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 5px;
}

.formula-note strong {
  color: var(--text-main);
  font-size: 11px;
}

.formula-note p {
  margin: 5px 0 0;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.7;
}

/* DYNAMIC PERFORMANCE CURVE */
.curve-panel {
  margin-top: 18px;
  padding: 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
}
.curve-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.curve-heading h2 {
  margin: 7px 0 5px;
  color: var(--text-main);
  font-family: 'Space Grotesk';
  font-size: 19px;
}
.curve-heading p, .curve-empty, .curve-disclaimer {
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.7;
}
.curve-controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  align-items: end;
  gap: 12px;
  margin-top: 20px;
}
.curve-controls label {
  display: block;
  margin: 0 0 8px;
  color: var(--text-main);
  font-size: 10px;
  font-weight: 700;
}
.curve-controls input {
  width: 100%;
  min-height: 42px;
  padding: 10px;
  color: var(--text-main);
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
}
.curve-controls .primary-button { margin: 0; white-space: nowrap; }
.curve-chart-wrap { margin-top: 25px; }
.curve-chart-meta { display: flex; justify-content: space-between; color: var(--text-muted); font-size: 9px; letter-spacing: .7px; }
.curve-chart { width: 100%; height: auto; margin-top: 10px; overflow: visible; }
.curve-table { display: grid; grid-template-columns: repeat(auto-fit, minmax(115px, 1fr)); gap: 8px; margin-top: 12px; }
.curve-table div { display: flex; flex-direction: column; gap: 5px; padding: 10px; background: var(--surface-secondary); border: 1px solid var(--border); border-radius: 4px; }
.curve-table span { color: var(--text-muted); font-size: 9px; }
.curve-table strong { color: var(--text-main); font-family: 'Space Grotesk'; font-size: 13px; }
.curve-empty { margin-top: 22px; padding: 22px; text-align: center; border: 1px dashed var(--border); border-radius: 4px; }

@media(max-width: 700px) {
  .curve-panel { padding: 18px; }
  .curve-controls { grid-template-columns: 1fr 1fr; }
  .curve-controls .primary-button { grid-column: 1 / -1; justify-content: center; }
}

@media(max-width: 390px) {
  .curve-controls { grid-template-columns: 1fr; }
}

@media(max-width: 700px) {
  .calculator-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .calculator-card {
    padding: 18px;
  }
}



/* FUNCTIONAL MODULES */
.comparison-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:25px; }
.comparison-grid h2 { color:var(--text-main); font-family:'Space Grotesk'; margin:8px 0 18px; }
.comparison-output { display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); margin-top:20px; padding-top:16px; color:var(--text-muted); font-size:11px; }
.comparison-output strong { color:var(--accent); font:700 24px 'Space Grotesk'; }
.comparison-output small { font:600 11px 'DM Sans'; }
.comparison-summary,.dataset-upload-card,.analysis-report-card,.report-card,.settings-card { margin-top:18px; padding:24px; background:var(--surface); border:1px solid var(--border); border-radius:5px; }
.comparison-summary h2,.dataset-upload-card h2,.report-card h2 { margin:0 0 9px; color:var(--text-main); font:700 18px 'Space Grotesk'; }
.comparison-summary p,.dataset-upload-card p,.report-card p { color:var(--text-muted); font-size:11px; line-height:1.7; }
.dataset-upload-card { text-align:center; padding:35px 20px; }
.upload-icon { width:52px;height:52px;display:grid;place-items:center;margin:0 auto 15px;background:var(--surface-secondary);color:var(--accent);border:1px solid var(--border);border-radius:6px; }
.dataset-upload-card input[type=file] { display:block; max-width:100%; margin:22px auto 12px; padding:12px; background:var(--surface-secondary); border:1px dashed var(--border); border-radius:4px; color:var(--text-main); }
.selected-file { display:flex;align-items:center;justify-content:center;gap:8px;color:var(--text-muted);font-size:10px;overflow-wrap:anywhere; }
.upload-actions { display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin-top:14px; }
.upload-actions .primary-button { margin-top:0; }
.dataset-metrics { margin:15px 0; }
.metric-small { font-size:20px!important; }
.table-wrap { overflow-x:auto; margin:18px 0; border:1px solid var(--border); border-radius:4px; }
.data-table { width:100%; border-collapse:collapse; font-size:10px; white-space:nowrap; }
.data-table th,.data-table td { padding:11px 13px; border-bottom:1px solid var(--border); text-align:right; color:var(--text-main); }
.data-table th { background:var(--surface-secondary); color:var(--text-muted); text-transform:uppercase; letter-spacing:.5px; }
.data-table tr:last-child td { border-bottom:0; }
.table-note { padding:0 12px; color:var(--text-muted); font-size:9px; }
.analysis-report-heading { display:flex;align-items:center;gap:13px;color:var(--accent); }
.analysis-report-heading div { display:flex;flex-direction:column;gap:4px; }
.analysis-report-heading strong { color:var(--text-main);font:700 17px 'Space Grotesk'; }
.analysis-report-heading span { color:var(--text-muted);font-size:10px; }
.analysis-report-card ul { margin:24px 0;padding-left:22px; }
.analysis-report-card li { padding:8px 0;color:var(--text-main);font-size:12px;line-height:1.7; }
.analysis-disclaimer { display:flex;align-items:flex-start;gap:9px;padding:13px;background:var(--surface-secondary);border:1px solid var(--border);border-radius:4px;color:var(--text-muted);font-size:10px;line-height:1.6; }
.analysis-disclaimer svg { flex:0 0 auto;color:var(--accent); }
.report-card { display:flex;flex-direction:column;align-items:flex-start;max-width:560px;padding:28px; }
.report-card > svg { color:var(--accent);margin-bottom:15px; }
.report-card .primary-button { margin-top:12px; }
.report-card .primary-button:disabled { opacity:.45;cursor:not-allowed; }
.settings-row { display:flex;justify-content:space-between;align-items:center;gap:18px;padding:17px 0;border-bottom:1px solid var(--border); }
.settings-row:last-child { border-bottom:0; }
.settings-row > div { display:flex;flex-direction:column;gap:5px; }
.settings-row strong { color:var(--text-main);font-size:12px; }
.settings-row span { color:var(--text-muted);font-size:10px; }
.api-status { display:flex;align-items:center;gap:8px;font-size:10px;font-weight:700;white-space:nowrap; }
.api-status i { width:8px;height:8px;border-radius:50%;background:#c16b42; }
.api-status.online i { background:#6f9474; }
.api-status.checking i { background:#c49a4a; }
@media(max-width:800px) { .comparison-grid { grid-template-columns:1fr; } .settings-row { align-items:flex-start;flex-direction:column; } }


.dataset-comparison-grid .calculator-card { min-width:0; }
.comparison-upload-copy { color:var(--text-muted);font-size:11px;margin:0 0 14px; }
.comparison-actions { margin:18px 0; }
.comparison-metric-detail { color:var(--text-muted);font-size:10px;margin:6px 0 0; }
.comparison-difference-summary { margin:18px 0; }
.comparison-difference-grid { display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:14px; }
.comparison-difference-grid > div { display:flex;flex-direction:column;gap:7px;padding:16px;background:var(--surface-secondary);border:1px solid var(--border);border-radius:4px; }
.comparison-difference-grid span { color:var(--text-muted);font-size:10px; }
.comparison-difference-grid strong { color:var(--text-main);font:700 24px 'Space Grotesk'; }
.comparison-chart-card { padding:22px;margin:18px 0;background:var(--surface);border:1px solid var(--border);border-radius:5px; }
.chart-mode-switch { display:flex;gap:7px;margin:15px 0; }
.chart-mode-switch button { padding:8px 12px;border:1px solid var(--border);border-radius:4px;background:var(--surface-secondary);color:var(--text-muted);font:600 10px inherit;cursor:pointer; }
.chart-mode-switch button.active { background:var(--accent);border-color:var(--accent);color:white; }
.comparison-legend { display:flex;gap:18px;color:var(--text-muted);font-size:10px;margin:10px 0; }
.comparison-legend span { display:flex;align-items:center;gap:7px; }
.comparison-legend i { width:17px;height:3px;display:inline-block;border-radius:4px; }
.legend-a { background:#c16b42; }.legend-b { background:#6486a5; }
.comparison-chart { display:block;width:100%;height:auto;min-height:170px;overflow:visible; }
@media(max-width:600px) { .comparison-difference-grid { grid-template-columns:1fr; }.comparison-chart-card { padding:14px; } }


/* ENGINE DIAGNOSTICS */
.diagnostic-upload-card { margin-top:22px; }
.diagnostic-results { margin-top:26px; }
.diagnostic-findings { margin:18px 0; padding:22px; background:var(--surface); border:1px solid var(--border); border-radius:5px; }
.diagnostic-findings > h2 { margin:0 0 16px; color:var(--text-main); font:700 18px 'Space Grotesk'; }
.diagnostic-finding { padding:17px; margin:12px 0; border:1px solid var(--border); border-left:4px solid #8b927e; border-radius:4px; background:var(--surface-secondary); }
.diagnostic-finding.severity-warning { border-left-color:#c18b45; }
.diagnostic-finding.severity-info { border-left-color:#6486a5; }
.diagnostic-finding-top { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.diagnostic-finding-top strong { color:var(--text-main); font:700 13px 'Space Grotesk'; }
.diagnostic-severity { padding:4px 8px; border-radius:3px; background:rgba(193,139,69,.13); color:#b17b34; font-size:9px; font-weight:800; text-transform:uppercase; }
.severity-info .diagnostic-severity { background:rgba(100,134,165,.13); color:#6486a5; }
.diagnostic-finding p { margin:10px 0; color:var(--text-main); font-size:11px; line-height:1.65; }
.diagnostic-recommendation { color:var(--text-muted); font-size:10px; line-height:1.65; }
.diagnostic-recommendation strong { color:var(--text-main); }
.diagnostic-code { display:inline-block; margin-top:10px; color:var(--text-muted); font-size:8px; letter-spacing:1px; }
@media(max-width:600px) { .diagnostic-findings { padding:14px; } .diagnostic-finding { padding:13px; } }

/* TORQUEIQ SCROLL FIX */

html,
body,
#app {
  min-height: 100%;
  height: auto !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
}

body {
  overscroll-behavior-y: auto !important;
  touch-action: pan-y;
}

.app {
  min-height: 100vh !important;
  height: auto !important;
  overflow: visible !important;
}

.app .main,
.app .content {
  height: auto !important;
  overflow: visible !important;
}

.app .sidebar {
  overflow-y: auto;
  overflow-x: hidden;
}
</style>
