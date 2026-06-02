"use client";

import { useEffect, useSyncExternalStore } from "react";
import { getUploadJobsSnapshot, subscribeUploadJobs } from "@/lib/upload-jobs";

export function UploadUnloadGuard() {
  const jobs = useSyncExternalStore(
    subscribeUploadJobs,
    getUploadJobsSnapshot,
    getUploadJobsSnapshot
  );

  useEffect(() => {
    const hasUncommittedUpload = jobs.some(
      (j) =>
        !j.fileId &&
        (j.status === "pending" ||
          j.status === "uploading" ||
          j.status === "uploaded" ||
          j.status === "analyzing")
    );
    if (!hasUncommittedUpload) return;

    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [jobs]);

  return null;
}
