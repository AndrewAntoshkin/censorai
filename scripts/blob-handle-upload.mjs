#!/usr/bin/env node
/**
 * Vercel Blob handleUpload (stdin JSON → stdout JSON).
 * Used by FastAPI when BLOB_READ_WRITE_TOKEN is only on the backend service.
 */
import { handleUpload } from "@vercel/blob/client";
import { readFileSync } from "node:fs";

const input = readFileSync(0, "utf8");
const { body, requestUrl, signature } = JSON.parse(input);

const request = {
  url: requestUrl,
  headers: { get: (name) => (name.toLowerCase() === "x-vercel-signature" ? signature : null) },
};

const result = await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async () => ({
    allowedContentTypes: [
      "video/mp4",
      "video/quicktime",
      "video/x-msvideo",
      "video/x-matroska",
      "video/webm",
      "application/octet-stream",
      "video/*",
    ],
    maximumSizeInBytes: 500 * 1024 * 1024,
    addRandomSuffix: true,
  }),
});

process.stdout.write(JSON.stringify(result));
