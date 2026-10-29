import { readFile } from "node:fs/promises";
import { basename, extname } from "node:path";

const baseUrl = "https://developer.amazon.com/api/appstore";

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

async function readResponseText(response) {
  const text = await response.text();
  return text.length > 0 ? text : "(empty response)";
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await readResponseText(response);
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${url} failed: ${response.status} ${response.statusText}: ${text}`);
  }
  return text === "(empty response)" ? {} : JSON.parse(text);
}

async function requestJsonWithResponse(url, options = {}) {
  const response = await fetch(url, options);
  const text = await readResponseText(response);
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${url} failed: ${response.status} ${response.statusText}: ${text}`);
  }
  return {
    data: text === "(empty response)" ? {} : JSON.parse(text),
    response,
  };
}

async function requestOk(url, options = {}) {
  const response = await fetch(url, options);
  const text = await readResponseText(response);
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${url} failed: ${response.status} ${response.statusText}: ${text}`);
  }
  return response;
}

function releaseKindForFile(file) {
  const ext = extname(file).toLowerCase();
  if (ext === ".apk") {
    return {
      label: "APK",
      resource: "apks",
      contentType: "application/vnd.android.package-archive",
    };
  }
  if (ext === ".aab") {
    return {
      label: "AAB",
      resource: "bundles",
      contentType: "application/octet-stream",
    };
  }
  throw new Error(`Unsupported Amazon release file extension "${ext}". Expected .apk or .aab`);
}

function describeAsset(asset) {
  return `id=${asset.id ?? "(missing)"} versionCode=${asset.versionCode ?? "(unknown)"} name=${asset.name ?? "(unknown)"}`;
}

function assetMatchesReleaseKind(asset, releaseKind) {
  const searchableValues = [
    asset.name,
    asset.fileName,
    asset.filename,
    asset.fileExtension,
    asset.extension,
    asset.type,
    asset.assetType,
  ]
    .filter((value) => typeof value === "string")
    .map((value) => value.toLowerCase());

  if (releaseKind.label === "APK") {
    return !searchableValues.some((value) => value.includes("aab") || value.includes("bundle"));
  }

  return !searchableValues.some((value) => value.includes("apk"));
}

async function listEditAssets(editId, resource) {
  const assets = await requestJson(`${baseUrl}/v1/applications/${appId}/edits/${editId}/${resource}`, {
    headers: jsonHeaders,
  });
  if (!Array.isArray(assets)) {
    throw new Error(`Amazon edit returned an unexpected ${resource} response: ${JSON.stringify(assets)}`);
  }
  return assets;
}

async function getAssetEtag(editId, resource, asset) {
  const response = await requestOk(`${baseUrl}/v1/applications/${appId}/edits/${editId}/${resource}/${asset.id}`, {
    headers: jsonHeaders,
  });
  const etag = response.headers.get("etag");
  if (!etag) {
    throw new Error(`Amazon did not return an ETag for ${describeAsset(asset)}`);
  }
  return etag;
}

async function replaceAsset(editId, resource, asset, releaseBytes) {
  const etag = await getAssetEtag(editId, resource, asset);
  await requestOk(`${baseUrl}/v1/applications/${appId}/edits/${editId}/${resource}/${asset.id}/replace`, {
    method: "PUT",
    headers: {
      ...authHeaders,
      "Content-Type": releaseKind.contentType,
      "If-Match": etag,
      fileName: basename(releaseFile),
    },
    body: releaseBytes,
  });
}

async function deleteAsset(editId, resource, asset) {
  const etag = await getAssetEtag(editId, resource, asset);
  await requestOk(`${baseUrl}/v1/applications/${appId}/edits/${editId}/${resource}/${asset.id}`, {
    method: "DELETE",
    headers: {
      ...jsonHeaders,
      "If-Match": etag,
    },
  });
}

async function uploadNewApk(editId, releaseBytes) {
  await requestOk(`${baseUrl}/v1/applications/${appId}/edits/${editId}/apks/upload`, {
    method: "POST",
    headers: {
      ...authHeaders,
      "Content-Type": releaseKind.contentType,
      fileName: basename(releaseFile),
    },
    body: releaseBytes,
  });
}

// A binary uploaded in the Developer Console as an app bundle occupies the
// edit's only APK slot. The API cannot upload bundles, so the release APK
// takes that slot: replace it, or delete it and upload when Amazon refuses.
async function replaceBundleSlotWithApk(editId, bundleSlots, releaseBytes) {
  if (bundleSlots.length !== 1 || !bundleSlots[0].id) {
    const slotDescriptions = bundleSlots.map(describeAsset).join(", ") || "(none)";
    throw new Error(`Expected exactly one app bundle slot for the APK to take over. Found: ${slotDescriptions}`);
  }
  const bundleSlot = bundleSlots[0];

  console.log(`Replacing app bundle ${describeAsset(bundleSlot)} with the APK`);
  try {
    await replaceAsset(editId, "apks", bundleSlot, releaseBytes);
    return;
  } catch (error) {
    console.log(`Amazon refused to replace the app bundle in place: ${error.message}`);
  }

  console.log(`Deleting app bundle ${describeAsset(bundleSlot)} from the edit`);
  await deleteAsset(editId, "apks", bundleSlot);
  console.log("Uploading the APK as the edit's new binary");
  await uploadNewApk(editId, releaseBytes);
}

const clientId = requireEnv("AMAZON_CLIENT_ID");
const clientSecret = requireEnv("AMAZON_CLIENT_SECRET");
const appId = requireEnv("AMAZON_APP_ID");
const releaseFile = requireEnv("AMAZON_RELEASE_FILE");
const releaseKind = releaseKindForFile(releaseFile);

console.log("Getting Amazon authentication token");
const tokenParams = new URLSearchParams({
  grant_type: "client_credentials",
  client_id: clientId,
  client_secret: clientSecret,
  scope: "appstore::apps:readwrite",
});
const token = await requestJson("https://api.amazon.com/auth/o2/token", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: tokenParams,
});
const authHeaders = {
  Authorization: `Bearer ${token.access_token}`,
};
const jsonHeaders = {
  ...authHeaders,
  "Content-Type": "application/json",
};

console.log("Checking for an open Amazon edit");
const { data: activeEdit, response: activeEditResponse } = await requestJsonWithResponse(`${baseUrl}/v1/applications/${appId}/edits`, {
  headers: jsonHeaders,
});
if (activeEdit.id) {
  const activeEditEtag = activeEditResponse.headers.get("etag");
  if (!activeEditEtag) {
    throw new Error(`Amazon did not return an ETag for open edit ${activeEdit.id}`);
  }
  console.log(`Deleting stale open edit ${activeEdit.id}`);
  await requestOk(`${baseUrl}/v1/applications/${appId}/edits/${activeEdit.id}`, {
    method: "DELETE",
    headers: {
      ...jsonHeaders,
      "If-Match": activeEditEtag,
    },
  });
}

console.log("Creating a fresh Amazon edit");
const edit = await requestJson(`${baseUrl}/v1/applications/${appId}/edits`, {
  method: "POST",
  headers: jsonHeaders,
});
if (!edit.id) {
  throw new Error("Amazon did not return an edit id");
}

const releaseBytes = await readFile(releaseFile);

console.log(`Finding ${releaseKind.label} slot to replace`);
const editAssets = await listEditAssets(edit.id, releaseKind.resource);
const matchingAssets = editAssets.filter((asset) => assetMatchesReleaseKind(asset, releaseKind));
if (matchingAssets.length > 0) {
  const asset = matchingAssets[0];
  if (!asset.id) {
    throw new Error(`Amazon ${releaseKind.label} asset did not include an id: ${JSON.stringify(asset)}`);
  }
  console.log(`Replacing ${releaseKind.label} ${describeAsset(asset)} via ${releaseKind.resource}`);
  await replaceAsset(edit.id, releaseKind.resource, asset, releaseBytes);
} else if (releaseKind.label === "APK") {
  await replaceBundleSlotWithApk(edit.id, editAssets, releaseBytes);
} else {
  const assetDescriptions = editAssets.map(describeAsset).join(", ") || "(none)";
  throw new Error(`Amazon edit has no ${releaseKind.label} asset to replace in ${releaseKind.resource}. Found: ${assetDescriptions}`);
}

const uploadedAssets = await listEditAssets(edit.id, "apks");
console.log(`Amazon edit ${edit.id} now holds: ${uploadedAssets.map(describeAsset).join(", ") || "(none)"}`);
console.log(`Amazon ${releaseKind.label} upload completed`);
