const fs = require("fs");
const path = require("path");
const https = require("https");

// --- Configuration ---
const REPO_OWNER = "IndieClub";
const REPO_NAME = "image-collection";
const BRANCH = "main";

// Whitelist: "folder_path": "prefix"
const TARGET_DIRS = {
	"": "", // Root folder, no prefix
	dapp: "dapp_", // dapp folder, prefix with dapp_
};

const IMG_EXTS = new Set([".png", ".jpg", ".jpeg", ".gif", ".webp"]);
const REQUEST_TIMEOUT_MS = 30000;

function formatTimestamp(date = new Date()) {
	const pad = (n) => String(n).padStart(2, "0");
	return [
		date.getFullYear(),
		pad(date.getMonth() + 1),
		pad(date.getDate()),
		pad(date.getHours()),
		pad(date.getMinutes()),
		pad(date.getSeconds()),
	].join("");
}

function shouldUseInsecureSSL() {
	const raw = (process.env.ALLOW_INSECURE_SSL || "true").toLowerCase();
	return raw === "1" || raw === "true" || raw === "yes";
}

function requestBuffer(url, timeoutMs = 10000, allowInsecureSSL = true, redirectCount = 0) {
	if (redirectCount > 5) {
		return Promise.reject(new Error(`Too many redirects: ${url}`));
	}

	return new Promise((resolve, reject) => {
		const req = https.request(
			url,
			{
				method: "GET",
				timeout: timeoutMs,
				headers: {
					"User-Agent": "nodejs-image-syncer",
					Accept: "application/vnd.github+json",
				},
				agent: new https.Agent({ rejectUnauthorized: !allowInsecureSSL }),
			},
			(res) => {
				const { statusCode = 0, headers } = res;

				if (statusCode >= 300 && statusCode < 400 && headers.location) {
					res.resume();
					resolve(requestBuffer(headers.location, timeoutMs, allowInsecureSSL, redirectCount + 1));
					return;
				}

				if (statusCode < 200 || statusCode >= 300) {
					const chunks = [];
					res.on("data", (chunk) => chunks.push(chunk));
					res.on("end", () => {
						const body = Buffer.concat(chunks).toString("utf8");
						reject(new Error(`HTTP ${statusCode} for ${url}. ${body.slice(0, 300)}`));
					});
					return;
				}

				const chunks = [];
				res.on("data", (chunk) => chunks.push(chunk));
				res.on("end", () => resolve(Buffer.concat(chunks)));
			}
		);

		req.on("timeout", () => {
			req.destroy(new Error(`Request timeout after ${timeoutMs}ms: ${url}`));
		});

		req.on("error", reject);
		req.end();
	});
}

async function requestJson(url, timeoutMs = 10000, allowInsecureSSL = true) {
	const buf = await requestBuffer(url, timeoutMs, allowInsecureSSL);
	return JSON.parse(buf.toString("utf8"));
}

async function requestBufferWithRetry(url, timeoutMs, allowInsecureSSL, retries = 1) {
	let lastErr;
	for (let i = 0; i <= retries; i += 1) {
		try {
			return await requestBuffer(url, timeoutMs, allowInsecureSSL);
		} catch (err) {
			lastErr = err;
			if (i < retries) {
				console.warn(`  Retry ${i + 1}/${retries} for: ${url}`);
			}
		}
	}
	throw lastErr;
}

async function syncImages() {
	const imageDict = {};
	const allowInsecureSSL = shouldUseInsecureSSL();

	if (allowInsecureSSL) {
		console.warn("Warning: SSL certificate verification is disabled (ALLOW_INSECURE_SSL=true).");
	}

	for (const [folder, prefix] of Object.entries(TARGET_DIRS)) {
		const apiUrl = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${folder}?ref=${BRANCH}`;
		console.log(`Scanning folder: /${folder}`);

		try {
			const items = await requestJson(apiUrl, REQUEST_TIMEOUT_MS, allowInsecureSSL);

			for (const item of items) {
				if (item.type !== "file") {
					continue;
				}

				const ext = path.extname(item.name).toLowerCase();
				if (!IMG_EXTS.has(ext)) {
					continue;
				}

				const nameBase = path.basename(item.name, ext);
				const finalKey = `${prefix}${nameBase}`;
				console.log(`  Encoding: ${finalKey}`);

				const imgData = await requestBufferWithRetry(item.download_url, REQUEST_TIMEOUT_MS, allowInsecureSSL, 1);
				imageDict[finalKey] = imgData.toString("base64");
			}
		} catch (error) {
			console.error(`  Error in /${folder}: ${error.message}`);
		}
	}

	fs.writeFileSync("images.json", JSON.stringify(imageDict, null, 4), "utf8");
	console.log(`\nSuccess! Saved ${Object.keys(imageDict).length} images to images.json`);

	const versionTimestamp = formatTimestamp();
	fs.writeFileSync("version.txt", versionTimestamp, "utf8");
	console.log(`version.txt: ${versionTimestamp}`);
}

syncImages().catch((error) => {
	console.error(`Fatal error: ${error.message}`);
	process.exitCode = 1;
});
