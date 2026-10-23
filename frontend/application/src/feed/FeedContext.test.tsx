import { cleanup, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TEST_CLIENT, TEST_USER, answer, answerFeed, renderWithCompany, stubApi } from "../testing";
import { useFeed } from "./context";
import { FeedProvider } from "./FeedContext";

function Headlines() {
  const { response } = useFeed();
  return <p>{response?.cards?.map((card) => card.headline).join(" · ") ?? "проверяю"}</p>;
}

describe("FeedProvider", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("asks once for the dashboard feed of the company on behalf of the user", async () => {
    const fetchMock = stubApi({ "POST /api/interpret": answerFeed });

    renderWithCompany(
      <FeedProvider>
        <Headlines />
        <Headlines />
      </FeedProvider>,
    );
    await answer();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      user_id: TEST_USER,
      client_id: TEST_CLIENT,
      role: "cfo",
      action_context: { type: "dashboard" },
    });
    expect(screen.getAllByText(/^Логистика в убытке · Банк ждёт снижения ключевой ставки/)).toHaveLength(2);
  });

  it("refuses to be read outside the provider", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => renderWithCompany(<Headlines />)).toThrow("useFeed must be used inside FeedProvider");
  });
});
