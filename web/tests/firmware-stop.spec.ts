// Firmware & USB -> Stop (app 0.4.24): the button is there only while something runs, and the answer to the stop is
// what the page shows, so the log and the state are on screen without waiting for the next poll.
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import FirmwareView from "../src/components/FirmwareView.vue";
import { state } from "../src/store";

type Job = { file: string; action: string; state: string; started: number } | null;

// The add-on: /api/firmware says what the job is, a stop ends it and answers with that same status.
function addon(job: Job, stop: { error?: string } = {}) {
  const posted: string[] = [];
  const status = () => ({ available: true, ports: [], logs: job ? [`ESPHome: compile`] : [], wifi: { state: "ready" },
    boards: {}, downloads: [], taken: { nodes: [], friendly: [] }, profiles: [{ file: "hall.yaml" }], job });
  vi.stubGlobal("fetch", vi.fn(async (url: string, options: any = {}) => {
    const path = String(url);
    if (options.method === "POST" && path.endsWith("api/firmware/jobs/cancel")) {
      posted.push(path);
      if (stop.error) return new Response(JSON.stringify({ error: stop.error }), { status: 400 });
      job = job && { ...job, state: "interrupted" };
      return new Response(JSON.stringify({ ...status(), logs: ["ESPHome: compile", "Stopped: build"] }));
    }
    return new Response(JSON.stringify(status()));
  }));
  return posted;
}

afterEach(() => { vi.unstubAllGlobals(); state.toast = null; });

describe("stopping a build", () => {
  it("offers Stop only while a job runs, and shows what the stop answered", async () => {
    const posted = addon({ file: "hall.yaml", action: "build", state: "running", started: 7 });
    const view = mount(FirmwareView);
    await flushPromises();
    expect(view.find("#firmware-stop").exists()).toBe(true);
    expect(view.find("#firmware-build").attributes("disabled")).toBeDefined();
    await view.find("#firmware-stop").trigger("click");
    await flushPromises();
    expect(posted).toHaveLength(1);
    expect(view.find("#firmware-status").text()).toContain("interrupted");
    expect(view.find("#firmware-log").text()).toContain("Stopped: build");
    // The job is over: Stop goes away and the three buttons come back.
    expect(view.find("#firmware-stop").exists()).toBe(false);
    expect(view.find("#firmware-build").attributes("disabled")).toBeUndefined();
  });

  it("has no Stop when nothing runs", async () => {
    addon(null);
    const view = mount(FirmwareView);
    await flushPromises();
    expect(view.find("#firmware-stop").exists()).toBe(false);
    expect(view.find("#firmware-build").attributes("disabled")).toBeUndefined();
  });

  it("says what went wrong and leaves the job alone when the stop is refused", async () => {
    addon({ file: "hall.yaml", action: "build", state: "running", started: 7 },
          { error: "No build or installation is running." });
    const view = mount(FirmwareView);
    await flushPromises();
    await view.find("#firmware-stop").trigger("click");
    await flushPromises();
    expect(view.find("#firmware-status").text()).toContain("running");
    expect(state.toast?.message).toBe("No build or installation is running.");
  });
});
