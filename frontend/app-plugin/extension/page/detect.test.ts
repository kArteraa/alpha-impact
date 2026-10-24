import { describe, expect, it } from "vitest";
import { PAGE_TEXT_MAX_CHARS } from "../config";
import { detectPage } from "./detect";

const PARAGRAPH =
  "Банк России на заседании в пятницу повысил ключевую ставку на 100 базисных пунктов, до 18% годовых. " +
  "Регулятор объяснил решение устойчиво высокой инфляцией и ростом кредитования.";

function page(body: string): Document {
  return new DOMParser().parseFromString(`<!doctype html><html><body>${body}</body></html>`, "text/html");
}

function lines(text: string): string[] {
  return text.split("\n");
}

const article = page(`
  <header><nav><a href="/">Главная</a><a href="/economics">Экономика</a></nav></header>
  <main>
    <article>
      <h1>ЦБ повысил ключевую ставку до 18%</h1>
      <p>${PARAGRAPH}</p>
      <p>${PARAGRAPH}</p>
      <p>${PARAGRAPH}</p>
    </article>
    <aside><p>Читайте также: курс рубля на неделе</p></aside>
  </main>
  <footer><p>АО «Коммерсантъ», ИНН 7707120552</p></footer>
`);

const counterparty = page(`
  <header><a href="/">Руспрофиль</a></header>
  <main>
    <h1>ООО «ТрансЛогистик»</h1>
    <dl><dt>ИНН</dt><dd>7707083893</dd><dt>ОГРН</dt><dd>1027700132195</dd></dl>
    <div>Основной вид деятельности: 49.41 Деятельность автомобильного грузового транспорта</div>
    <div>Юридический адрес: Республика Татарстан, г. Казань</div>
  </main>
  <footer>ООО «Руспрофиль», ИНН 7728012325</footer>
`);

describe("detectPage on a business media article", () => {
  it("takes the headline as the first line and the paragraphs as the body", () => {
    const detected = detectPage(article, "https://www.kommersant.ru/doc/7000001");

    expect(detected?.pageType).toBe("article");
    expect(detected?.page.url).toBe("https://www.kommersant.ru/doc/7000001");
    expect(lines(detected!.page.text)).toEqual(["ЦБ повысил ключевую ставку до 18%", PARAGRAPH, PARAGRAPH, PARAGRAPH]);
    expect(detected?.page.entities).toEqual([]);
  });

  it("ignores a rubric page without a long enough body", () => {
    const rubric = page(`<h1>Экономика</h1><p>Новости экономики</p><p>Все материалы рубрики</p>`);

    expect(detectPage(rubric, "https://www.kommersant.ru/rubric/3")).toBeNull();
  });

  it("drops tracking labels from the address but keeps the page's own parameters", () => {
    const detected = detectPage(article, "https://www.kommersant.ru/doc/1?utm_source=tg&from=main&id=7&yclid=5");

    expect(detected?.page.url).toBe("https://www.kommersant.ru/doc/1?id=7");
  });

  it("recognises the named subdomains of rates and tender sites", () => {
    const rates = page(`<h1>Курс USD/RUB</h1><p>USD 92,50</p>`);
    expect(detectPage(rates, "https://ru.investing.com/currencies/usd-rub")?.pageType).toBe("fx_rate");
    const tender = page(`<div>№ 0373200041524000123</div><section><span>Предмет договора</span><span>Ремонт кровли</span></section>`);
    expect(detectPage(tender, "https://223.rts-tender.ru/supplier/auction/1")?.pageType).toBe("tender");
  });

  it("drops the fragment from the address", () => {
    expect(detectPage(article, "https://www.kommersant.ru/doc/7000001#comments")?.page.url).toBe(
      "https://www.kommersant.ru/doc/7000001",
    );
  });

  it("takes the headline outside the site navigation", () => {
    const branded = page(`<header><nav><h1>Коммерсантъ</h1></nav></header><h1>Ставка 18%</h1><p>${PARAGRAPH}</p><p>${PARAGRAPH}</p>`);

    expect(lines(detectPage(branded, "https://www.kommersant.ru/doc/2")!.page.text)[0]).toBe("Ставка 18%");
  });

  it("ignores an RSS feed opened on the media site", () => {
    const feed = new DOMParser().parseFromString("<rss><channel><title>Экономика</title></channel></rss>", "application/xml");

    expect(detectPage(feed, "https://www.kommersant.ru/RSS/section-economics.xml")).toBeNull();
  });

  it("cuts the text to the configured length", () => {
    const long = page(`<h1>Ставка</h1>${`<p>${PARAGRAPH}</p>`.repeat(30)}`);

    expect(detectPage(long, "https://www.vedomosti.ru/economics/1")?.page.text).toHaveLength(PAGE_TEXT_MAX_CHARS);
  });
});

describe("detectPage on a counterparty check service", () => {
  it("sends the company name, the page text and the company INN", () => {
    const detected = detectPage(counterparty, "https://www.rusprofile.ru/id/123");

    expect(detected?.pageType).toBe("counterparty");
    expect(lines(detected!.page.text)[0]).toBe("ООО «ТрансЛогистик»");
    expect(detected?.page.text).toContain("49.41 Деятельность автомобильного грузового транспорта");
    expect(detected?.page.entities).toEqual(["inn:7707083893"]);
  });

  it("sends only the company's own INN, not its founders' or related companies'", () => {
    const founders = page(`
      <h1>ООО «ТрансЛогистик»</h1><p>ИНН 7707083893</p>
      <section><h2>Учредители</h2><p>Иванов Иван Иванович, ИНН 500100732259</p></section>
    `);

    expect(detectPage(founders, "https://www.rusprofile.ru/id/123")?.page.entities).toEqual(["inn:7707083893"]);
  });

  it("sends the company name once", () => {
    const text = detectPage(counterparty, "https://www.rusprofile.ru/id/123")!.page.text;

    expect(lines(text).filter((line) => line === "ООО «ТрансЛогистик»")).toHaveLength(1);
  });

  it("leaves out hidden blocks", () => {
    const hidden = page(`<h1>ООО «ТрансЛогистик»</h1><p>ИНН 7707083893</p><div hidden>Похожие компании</div><div aria-hidden="true">Реклама</div>`);

    const text = detectPage(hidden, "https://www.rusprofile.ru/id/123")!.page.text;
    expect(text).not.toContain("Похожие компании");
    expect(text).not.toContain("Реклама");
  });

  it("leaves out the service's own INN in the footer", () => {
    expect(detectPage(counterparty, "https://www.rusprofile.ru/id/123")?.page.text).not.toContain("7728012325");
  });

  it("sends each INN once", () => {
    const twice = page(`<h1>ООО «ТрансЛогистик»</h1><p>ИНН 7707083893</p><p>ИНН организации 7707083893</p>`);

    expect(detectPage(twice, "https://checko.ru/company/1")?.page.entities).toEqual(["inn:7707083893"]);
  });

  it("ignores a person's page: only a legal entity with a ten-digit INN is a counterparty", () => {
    const person = page(`<h1>Иванов Иван Иванович</h1><p>ИНН 500100732259</p><p>Учредитель 3 компаний</p>`);

    expect(detectPage(person, "https://www.rusprofile.ru/person/ivanov-500100732259")).toBeNull();
  });

  it("ignores a person's page even when it lists the person's companies", () => {
    const person = page(`<h1>Иванов Иван Иванович</h1><p>ИНН 500100732259</p><p>Руководитель ООО «Ромашка», ИНН 7707083893</p>`);

    expect(detectPage(person, "https://www.rusprofile.ru/person/ivanov-500100732259")).toBeNull();
  });

  it("keeps the from parameter of a rates or tender page", () => {
    const rates = page(`<h1>Курс USD/RUB</h1><p>USD 92,50</p>`);

    expect(detectPage(rates, "https://ru.investing.com/currencies/usd-rub?from=2026-01-01")?.page.url).toBe(
      "https://ru.investing.com/currencies/usd-rub?from=2026-01-01",
    );
  });

  it("hides a person's INN in the text it sends", () => {
    const founders = page(`
      <h1>ООО «ТрансЛогистик»</h1><p>ИНН 7707083893</p>
      <section><h2>Учредители</h2><p>Иванов Иван Иванович, ИНН 500100732259</p></section>
    `);

    const text = detectPage(founders, "https://www.rusprofile.ru/id/123")!.page.text;
    expect(text).not.toContain("500100732259");
    expect(text).toContain("7707083893");
  });

  it("ignores a page without a valid INN", () => {
    const wrong = page(`<h1>ООО «ТрансЛогистик»</h1><dl><dt>ИНН</dt><dd>7707083894</dd></dl>`);

    expect(detectPage(wrong, "https://www.rusprofile.ru/id/123")).toBeNull();
  });
});

describe("detectPage on a tender", () => {
  it("puts the subject first and the purchase number second", () => {
    const tender = page(`
      <div><span>44-ФЗ Электронный аукцион</span><span>№ 0373200041524000123</span></div>
      <section><span>Объект закупки</span><span>Поставка офисной бумаги формата А4</span></section>
      <section><span>Начальная (максимальная) цена контракта</span><span>1 250 000,00 ₽</span></section>
    `);

    const detected = detectPage(tender, "https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html");

    expect(detected?.pageType).toBe("tender");
    expect(lines(detected!.page.text).slice(0, 2)).toEqual([
      "Поставка офисной бумаги формата А4",
      "Закупка № 0373200041524000123",
    ]);
    expect(lines(detected!.page.text).filter((line) => line === "Поставка офисной бумаги формата А4")).toHaveLength(1);
  });

  it("reads a subject written on the label line", () => {
    const tender = page(`<p>Процедура №32414012345</p><p>Предмет договора: Ремонт кровли склада</p>`);

    expect(lines(detectPage(tender, "https://www.b2b-center.ru/market/view.html")!.page.text).slice(0, 2)).toEqual([
      "Ремонт кровли склада",
      "Закупка № 32414012345",
    ]);
  });

  it("ignores a tender page without a subject", () => {
    const tender = page(`<p>Закупка № 0373200041524000123</p><p>Документация</p>`);

    expect(detectPage(tender, "https://zakupki.gov.ru/epz/order/1")).toBeNull();
  });
});

describe("detectPage on exchange rates", () => {
  it("sends the heading and the rates", () => {
    const rates = page(`<h1>Официальные курсы валют</h1><table><tr><td>USD</td><td>Доллар США</td><td>81,25</td></tr></table>`);

    const detected = detectPage(rates, "https://www.cbr.ru/currency_base/daily/");

    expect(detected?.pageType).toBe("fx_rate");
    expect(lines(detected!.page.text)[0]).toBe("Официальные курсы валют");
    expect(detected?.page.text).toContain("Доллар США");
  });
});

describe("detectPage on pages that only look like rates", () => {
  it("ignores a page of a rates site without a currency", () => {
    const release = page(`<h1>Вакансии Банка России</h1><p>Приглашаем на работу аналитиков</p>`);

    expect(detectPage(release, "https://www.cbr.ru/vacancies/")).toBeNull();
  });
});

describe("detectPage on other sites", () => {
  it.each(["https://example.com/news/1", "https://kommersant.ru.example.com/doc/1", "https://notrbc.ru/news/1"])(
    "stays silent on %s even with article markup",
    (url) => {
      expect(detectPage(article, url)).toBeNull();
    },
  );

  it.each(["https://online.sbis.ru/page/company/1", "https://lk.rusprofile.ru/id/123"])(
    "stays out of other subdomains such as private workspaces on %s",
    (url) => {
      expect(detectPage(counterparty, url)).toBeNull();
    },
  );
});
