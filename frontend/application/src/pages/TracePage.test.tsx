import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type Reply, stubApi } from "../testing";
import { NEWS_SOURCE, REPORT_SOURCE, TRACE } from "../trace/trace.fixture";
import { TracePage } from "./TracePage";

function renderTrace(reply: Reply = [200, TRACE]) {
  const fetchMock = stubApi({ [`GET /api/trace/${TRACE.id}`]: reply, "POST /api/feedback": [204, null] });
  render(
    <MemoryRouter initialEntries={[`/trace/${TRACE.id}`]}>
      <Routes>
        <Route path="/trace/:id" element={<TracePage />} />
      </Routes>
    </MemoryRouter>,
  );
  return fetchMock;
}

function stepNames() {
  return Array.from(document.querySelectorAll(".trace-step-name"), (step) => step.textContent);
}

function flat(text: string | null | undefined) {
  return text?.replace(/\s/g, " ");
}

async function loaded() {
  return screen.findByRole("region", { name: "Шаги" });
}

describe("TracePage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("reads the steps of the agent from top to bottom in plain words", async () => {
    renderTrace();
    await loaded();

    expect(stepNames()).toEqual([
      "Профиль компании",
      "Агрегаты получателя",
      "Отбор новостей",
      "План агента",
      "Позиция банка по теме",
      "Черновик карточки",
      "Критик, круг 1",
      "Переписанный черновик",
      "Критик, круг 2",
      "Итог: карточка",
    ]);
  });

  it("shows the time, the tokens, the model and the cost of a model step", async () => {
    renderTrace();
    await loaded();

    const plan = screen.getByText("План агента").closest("summary");
    expect(flat(plan?.querySelector(".trace-step-meta")?.textContent)).toBe(
      "4 700 мс · 4 812 → 236 токенов · z-ai/glm-5.3-flash · 0,06 ₽",
    );
    const profile = screen.getByText("Профиль компании").closest("summary");
    expect(flat(profile?.querySelector(".trace-step-meta")?.textContent)).toBe("3 мс");
  });

  it("does not round a cost below a kopeck to zero", async () => {
    const steps = TRACE.steps.map((step) => (step.step === "critic" ? { ...step, cost_rub: 0.004 } : step));
    renderTrace([200, { ...TRACE, steps }]);
    await loaded();

    const critic = screen.getByText("Критик, круг 2").closest("summary");
    expect(flat(critic?.querySelector(".trace-step-meta")?.textContent)).toBe("1 700 мс · 1 590 → 30 токенов · 0,004 ₽");
    expect(flat(document.querySelector(".trace-facts")?.textContent)).toContain("Стоимость0,498 ₽");
  });

  it("opens the arguments of a tool call and the draft of the card", async () => {
    renderTrace();
    await loaded();
    const tool = screen.getByText("Позиция банка по теме").closest("details");
    expect(tool?.hasAttribute("open")).toBe(false);

    fireEvent.click(screen.getByText("Позиция банка по теме"));
    fireEvent.click(screen.getByText("Черновик карточки"));

    expect(tool?.hasAttribute("open")).toBe(true);
    expect(within(tool as HTMLElement).getByText("Аргументы")).toBeTruthy();
    expect(within(tool as HTMLElement).getByText("trade_logistics")).toBeTruthy();
    const draft = screen.getByText("Черновик карточки").closest("details") as HTMLElement;
    expect(within(draft).getByText(/"headline": "Перевозчики дорожают"/).tagName).toBe("PRE");
  });

  it("sums up the request, the time, the tokens and the cost", async () => {
    renderTrace();
    await loaded();

    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Как получен вывод");
    expect(flat(document.querySelector(".page-sub")?.textContent)).toBe(
      "Платёж 1 500 000 ₽ · Финансовый директор · 23 октября 2026 г. в 11:15",
    );
    expect(screen.getByText("22,0 с")).toBeTruthy();
    expect(flat(document.querySelector(".trace-facts")?.textContent)).toBe(
      "Токены28 832 → 2 536Моделиz-ai/glm-5.3-flashШагов10Стоимость0,53 ₽",
    );
  });

  it("lists the critic verdicts round by round", async () => {
    renderTrace();
    await loaded();

    const verdicts = screen.getByRole("region", { name: "Проверка критика" });
    const items = Array.from(verdicts.querySelectorAll("li"));
    expect(items.map((item) => item.textContent)).toEqual([
      "Круг 1: Пересказ — карточка опирается меньше чем на два источника",
      "Круг 2: замечаний нет",
    ]);
    expect(items.map((item) => item.getAttribute("data-ok"))).toEqual(["false", "true"]);
  });

  it("ends with the card whose sources lead to the article and the report page", async () => {
    renderTrace();
    await loaded();

    const result = screen.getByRole("region", { name: "Итог" });
    const basis = within(result).getByRole("region", { name: "На чём основан вывод" });
    expect(within(basis).getByRole("link", { name: NEWS_SOURCE.title ?? "" }).getAttribute("href")).toBe(NEWS_SOURCE.url);
    expect(within(basis).getByRole("link", { name: REPORT_SOURCE.title ?? "" }).getAttribute("href")).toBe(
      `/api${REPORT_SOURCE.url}`,
    );
  });

  it("takes feedback on the resulting card", async () => {
    const fetchMock = renderTrace();
    await loaded();

    fireEvent.click(screen.getByRole("button", { name: "Полезно" }));

    const [url, init] = fetchMock.mock.calls.at(-1) ?? [];
    expect(url).toBe("/api/feedback");
    expect(JSON.parse(String(init?.body))).toEqual({ card_id: TRACE.result?.cards?.[0].id, useful: true });
  });

  it("shows the silence the request ended with", async () => {
    renderTrace([200, { ...TRACE, result: { silent: true, silent_reason: "Нет значимых событий для этого действия" } }]);
    await loaded();

    const result = screen.getByRole("region", { name: "Итог" });
    expect(within(result).getByRole("status").textContent).toContain("Ничего важного по этому действию");
    expect(within(result).getByText("Нет значимых событий для этого действия")).toBeTruthy();
  });

  it("marks the failed end and has no result when the request failed", async () => {
    const failed = { ...TRACE.steps[9], name: "failed", output_summary: "ModelUnavailable" };
    renderTrace([200, { ...TRACE, result: null, steps: [...TRACE.steps.slice(0, 9), failed] }]);
    await loaded();

    expect(screen.queryByRole("region", { name: "Итог" })).toBeNull();
    const steps = Array.from(document.querySelectorAll(".trace-step"), (step) => step.getAttribute("data-failed"));
    expect(steps.at(-1)).toBe("true");
    expect(steps.slice(0, -1).every((value) => value === "false")).toBe(true);
  });

  it("shows that the trace is loading", async () => {
    renderTrace();

    expect(screen.getByText("Загружаю трассу").closest("[aria-busy]")?.getAttribute("aria-busy")).toBe("true");
    await loaded();
  });

  it.each([404, 403])("says calmly that the trace is not found on %i", async (code) => {
    renderTrace([code, "Unknown trace"]);

    expect(await screen.findByText(/^Трасса не найдена/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "На главную" }).getAttribute("href")).toBe("/");
  });

  it("admits that the trace did not load", async () => {
    renderTrace([500, "boom"]);

    expect(await screen.findByText("Не удалось загрузить трассу")).toBeTruthy();
  });

  it("leads back to the main screen", () => {
    renderTrace();

    expect(screen.getByRole("link", { name: "← Главная" }).getAttribute("href")).toBe("/");
  });
});
