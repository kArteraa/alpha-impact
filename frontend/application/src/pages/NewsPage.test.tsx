import { mockResponses } from "@alpha-impact/plugin";
import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { answer, askedContext, panelState, placeholderSteps, renderWithCompany, stubApi } from "../testing";
import { NewsPage } from "./NewsPage";

const NEWS = "Банк России сохранил ключевую ставку\nСовет директоров сохранил ставку на уровне 14%.";
const SOURCE = "https://demo.example/cbr-key-rate";

function render() {
  return renderWithCompany(<NewsPage />, { path: "/news/new" });
}

function paste(text: string) {
  fireEvent.change(screen.getByLabelText("Текст новости"), { target: { value: text } });
}

function link(url: string) {
  fireEvent.change(screen.getByLabelText("Ссылка на источник"), { target: { value: url } });
}

function analyseButton() {
  return screen.getByRole("button", { name: "Разобрать новость" }) as HTMLButtonElement;
}

function analyse() {
  fireEvent.click(analyseButton());
}

describe("NewsPage", () => {
  let fetchMock: ReturnType<typeof stubApi>;

  beforeEach(() => {
    vi.useFakeTimers();
    fetchMock = stubApi({ "POST /api/interpret": [200, mockResponses.cards] });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("keeps the button disabled until there is text", () => {
    render();
    expect(analyseButton().disabled).toBe(true);

    paste("   \n ");
    expect(analyseButton().disabled).toBe(true);

    paste(NEWS);
    expect(analyseButton().disabled).toBe(false);
  });

  it("asks nothing while the news is only typed", async () => {
    render();
    paste(NEWS);
    link(SOURCE);
    await answer();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(panelState()).toBeUndefined();
    expect(placeholderSteps()).toEqual(["true", "true"]);
  });

  it("sends the trimmed text as a page without a link", async () => {
    render();
    paste(`\n${NEWS}\n  `);
    analyse();
    await answer();

    expect(askedContext(fetchMock, 0)).toEqual({ type: "page", url: "", text: NEWS });
  });

  it("sends the source link with the text", async () => {
    render();
    link(SOURCE);
    paste(NEWS);
    analyse();
    await answer();

    expect(askedContext(fetchMock, 0)).toEqual({ type: "page", url: SOURCE, text: NEWS });
  });

  it("says it is marking up the news while waiting", () => {
    render();
    paste(NEWS);
    analyse();

    expect(panelState()).toBe("checking");
    expect(screen.getByText("Размечаю новость и смотрю, что она значит для компании")).toBeTruthy();
  });

  it("admits it did not manage in time and offers a retry", async () => {
    fetchMock = stubApi({ "POST /api/interpret": [422, { detail: "model API /chat/completions timed out" }] });
    render();
    paste(NEWS);
    analyse();
    await answer();

    expect(panelState()).toBe("failed");
    expect(screen.getByText("Не успел разобрать новость")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Попробовать ещё раз" }));
    await answer();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("analyses the same news again when the button is pressed after a failure", async () => {
    fetchMock = stubApi({ "POST /api/interpret": [503, { detail: "unavailable" }] });
    render();
    paste(NEWS);
    analyse();
    await answer();
    expect(panelState()).toBe("failed");

    analyse();
    await answer();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("keeps the button disabled while the news is analysed", () => {
    render();
    paste(NEWS);
    analyse();

    expect(analyseButton().disabled).toBe(true);
  });

  it("does not show the previous card while another news item is analysed", async () => {
    render();
    paste(NEWS);
    analyse();
    await answer();
    expect(panelState()).toBe("cards");

    paste("Минфин разместил ОФЗ\nСпрос превысил предложение вдвое.");
    analyse();

    expect(panelState()).toBe("checking");
    expect(screen.getByText("Размечаю новость и смотрю, что она значит для компании")).toBeTruthy();
  });

  it("says calmly that the news does not matter for the company", async () => {
    fetchMock = stubApi({ "POST /api/interpret": [200, mockResponses.silent] });
    render();
    paste(NEWS);
    analyse();
    await answer();

    expect(panelState()).toBe("silent");
    expect(screen.getByRole("status").textContent).toContain("Ничего важного для компании в этой новости");
  });

  it("shows the card with a link to its trace", async () => {
    render();
    paste(NEWS);
    analyse();
    await answer();

    expect(panelState()).toBe("cards");
    expect(screen.getByRole("link", { name: "Как получен вывод" }).getAttribute("href")).toBe(
      `/trace/${mockResponses.cards.cards[0].trace_id}`,
    );
  });

  it("analyses an edited text only on a new press", async () => {
    render();
    paste(NEWS);
    analyse();
    await answer();

    paste(`${NEWS}\nКредиты подешевеют.`);
    await answer();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    analyse();
    await answer();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(askedContext(fetchMock, 1).text).toBe(`${NEWS}\nКредиты подешевеют.`);
  });
});
