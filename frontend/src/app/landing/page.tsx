import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  FileText,
  Scale as ScaleIcon,
  Tv,
  Play,
  Send,
  Lock,
  Server,
  Trash2,
  Eye,
  CheckCircle2,
} from "lucide-react";
import { ContactForm } from "@/components/landing/contact-form";
import { FooterLoginLink } from "@/components/landing/footer-login-link";
import { FooterRegisterLink } from "@/components/landing/footer-register-link";
import { TryPlacementButton } from "@/components/landing/try-placement-button";
import { HeroRays } from "@/components/landing/hero-rays";
import { LandingLoginHost } from "@/components/landing/landing-login-host";
import { LandingNav } from "@/components/landing/landing-nav";
import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";

export const metadata: Metadata = {
  title: "фреймчек — AI-анализ видеоконтента",
  description:
    "Автоматическая проверка видео на соответствие требованиям законодательства РФ. Быстрее ручной проверки — первичный триаж перед экспертизой.",
};

function Logo({ light = false }: { light?: boolean }) {
  return (
    <span
      className={`landing-logo ${light ? "text-[var(--v7-white)]" : "text-[var(--v7-ink)]"}`}
    >
      фреймчек
    </span>
  );
}

function Hero() {
  return (
    <section className="landing-hero relative flex flex-col overflow-hidden bg-[var(--v7-black)] text-center">
      <div className="landing-hero-bg absolute inset-0">
        <HeroRays />
      </div>
      <div className="landing-hero-vignette pointer-events-none absolute inset-0" aria-hidden />
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 pb-8 pt-[calc(var(--landing-header-total)+2.5rem)] sm:pt-[calc(var(--landing-header-total)+3.5rem)]">
        <div className="mx-auto max-w-3xl">
          <h1 className="landing-display font-normal">
            <span className="text-[var(--v7-text-muted)]">
              Перестаньте просматривать видео вручную.
            </span>
            <br />
            <span className="font-medium text-[var(--v7-white-warm)]">Начните принимать решения.</span>
          </h1>
          <p className="mx-auto mt-7 max-w-2xl text-[var(--landing-body)] leading-[1.7] text-[var(--v7-text-subtle)]">
            фреймчек проводит{" "}
            <span className="font-medium text-[var(--v7-white-warm)]">покадровый AI-анализ</span>, формирует{" "}
            <span className="font-medium text-[var(--v7-white-warm)]">отчёты с таймкодами</span> и сверяет контент с{" "}
            <span className="font-medium text-[var(--v7-white-warm)]">подсказки по реестрам Минюста</span>. Два режима:{" "}
            <span className="font-medium text-[var(--v7-white-warm)]">модерация</span> и{" "}
            <span className="font-medium text-[var(--v7-white-warm)]">продакт плейсмент</span>.
          </p>
          <div className="mt-10">
            <a
              href="#cta"
              className="inline-flex items-center gap-2 rounded-full bg-[var(--v7-white)] px-8 py-3.5 text-[var(--landing-body)] font-medium text-[var(--v7-ink)] transition-colors hover:bg-[var(--v7-cream)]"
            >
              Оставить заявку
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
      <div className="relative z-10 mt-auto">
        <LogoMarquee />
      </div>
    </section>
  );
}

function LogoMarquee() {
  const items = [
    "ТВ-каналы",
    "Онлайн-кинотеатры",
    "Продакшн-студии",
    "Дистрибьюторы",
    "Медиабиблиотеки",
    "Рекламные агентства",
  ];
  const row = [...items, ...items];

  return (
    <div className="relative border-t border-[var(--v7-border)] px-6 pb-12 pt-10 sm:pb-14">
      <p className="mb-8 text-center text-[14px] uppercase tracking-[0.5px] text-[var(--v7-text-faint)]">
        Для команд, которые отвечают за{" "}
        <em className="text-[var(--v7-text-muted)] not-italic">соответствие контента</em>
      </p>
      <div className="overflow-hidden">
        <div className="landing-marquee-track flex w-max gap-16 px-6">
          {row.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="shrink-0 text-[var(--landing-body)] font-medium tracking-tight text-[var(--v7-text-faint)]"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function WorkflowGrid() {
  const workflows = [
    {
      icon: Tv,
      title: "Проверка перед эфиром",
      description: "Скрининг выпуска или серии перед выходом в сетку вещания",
      before: "3–5 ч",
      after: "5–20 мин",
    },
    {
      icon: Play,
      title: "Анализ каталога",
      description: "Пакетная проверка библиотеки перед публикацией на платформе",
      before: "100+ ч",
      after: "< 10 ч",
    },
    {
      icon: Send,
      title: "Контроль от подрядчиков",
      description: "Автоматическая проверка материалов от внешних продакшенов",
      before: "2–3 дня",
      after: "часы",
    },
    {
      icon: Eye,
      title: "Предэкспертиза",
      description: "Отсев проблемных фрагментов до финальной юридической экспертизы",
      before: "8 000+ ₽/ч",
      after: "от 600 ₽/ч",
    },
  ];

  return (
    <section id="workflows" className="border-t border-[var(--v7-border)] bg-[var(--v7-dark)] text-[var(--v7-white)]">
      <div className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <SectionHeading
          dark
          line1="Сценарии,"
          line2="которые внедряют первыми."
          subtitle="Первичная проверка видео встраивается в существующие процессы — от эфира до архивного каталога."
          className="mb-14"
        />
        <div className="grid border border-[var(--v7-border)] sm:grid-cols-2 lg:grid-cols-4">
          {workflows.map((item, i) => (
            <div
              key={item.title}
              className={`flex flex-col p-6 sm:p-7 ${
                i % 2 === 0 ? "border-[var(--v7-border)] sm:border-r" : ""
              } ${i < 2 ? "border-b border-[var(--v7-border)] lg:border-b-0" : ""} ${
                i < 3 ? "lg:border-r lg:border-[var(--v7-border)]" : ""
              }`}
            >
              <item.icon className="mb-5 h-5 w-5 text-[var(--v7-text-faint)]" strokeWidth={1.5} />
              <h3 className="mb-2 text-sm font-medium text-[var(--v7-white-warm)]">{item.title}</h3>
              <p className="mb-8 flex-1 text-xs leading-relaxed text-[var(--v7-text-on-dark-secondary)]">
                {item.description}
              </p>
              <div className="space-y-1 border-t border-[var(--v7-border)] pt-4 text-xs">
                <div className="flex justify-between text-[var(--v7-text-on-dark-tertiary)]">
                  <span>До</span>
                  <span>{item.before}</span>
                </div>
                <div className="flex justify-between font-medium text-[var(--v7-white-warm)]">
                  <span>с фреймчек</span>
                  <span className="text-[var(--v7-orange)]">{item.after}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-px grid border border-t-0 border-[var(--v7-border)] sm:grid-cols-3">
          {[
            { value: "5–20 мин", label: "на час видео (типично)" },
            { value: "18+", label: "категорий проверки" },
            { value: "2", label: "режима анализа" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="border-[var(--v7-border)] px-6 py-8 text-center sm:border-r last:sm:border-r-0"
            >
              <div className="text-4xl font-medium tracking-[-0.03em] text-[var(--v7-white-warm)] sm:text-5xl">
                {stat.value}
              </div>
              <div className="mt-2 text-xs text-[var(--v7-text-on-dark-secondary)]">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function PlatformSection() {
  const stats = [
    { v: "100+", l: "часов обработки в сутки" },
    { v: "24/7", l: "очередь без простоя" },
    { v: "API", l: "интеграция в пайплайн" },
  ];

  return (
    <section id="platform" className="bg-[var(--v7-cream-soft)] text-[var(--v7-ink)]">
      <div className="landing-section">
        <SectionHeading
          line1="Платформа для"
          line2="проверки видео."
          subtitle="Загрузка, покадровый AI-анализ и структурированный отчёт с таймкодами — готов к работе эксперта."
          className="mb-14"
        />
        <div className="landing-grid lg:grid-cols-[1.35fr_1fr]">
          <BentoCard label="Отчёт по сценам" title="Каждый риск с таймкодом">
            <ReportPreview />
          </BentoCard>
          <div className="grid gap-px bg-[var(--v7-grid-line)]">
            {stats.map((s) => (
              <div key={s.l} className="landing-cell landing-cell--cream flex flex-col justify-center">
                <div className="landing-stat-value text-[var(--v7-ink)]">{s.v}</div>
                <p className="mt-2 text-sm text-[var(--v7-text-on-light-muted)]">{s.l}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

const CHECK_CATEGORIES = [
  "Наркотики",
  "Оружие",
  "Насилие",
  "Сексуальный контент",
  "Нецензурная лексика",
  "Алкоголь",
  "Курение",
  "Незаконные действия",
  "Жестокость к животным",
  "Запрещённая символика",
  "Текст в кадре",
  "Дискредитация ценностей",
  "Пропаганда",
  "Героизация преступлений",
  "ЛГБТ-пропаганда",
  "Суицид и самоповреждение",
  "Иноагенты",
  "Педофилия",
  "Чрезмерная жестокость",
];

function CategoriesSection() {
  return (
    <section id="categories" className="border-t border-[var(--v7-border-light)] bg-[var(--v7-white)] text-[var(--v7-ink)]">
      <div className="landing-section">
        <SectionHeading
          line1="18+ направлений"
          line2="проверки."
          subtitle="Каждая категория — отдельный тип риска с таймкодом, уровнем и рекомендацией для монтажа или маркировки."
          className="mb-12"
        />
        <div className="landing-grid">
          <div className="landing-cell landing-cell--white">
            <p className="landing-kicker text-[var(--v7-ink-muted)]">Категории риска</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {CHECK_CATEGORIES.map((cat) => (
                <span key={cat} className="landing-tag">
                  {cat}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ProductPlacementSection() {
  const steps = [
    {
      title: "Задаёте продукт",
      text: "Указываете, что нужно встроить — напиток, гаджет, упаковку.",
    },
    {
      title: "AI просматривает видео",
      text: "Система ищет нативные слоты: замена предмета в кадре или подходящий контекст сцены.",
    },
    {
      title: "Получаете таймкоды",
      text: "Отчёт с suitability, типом слота и заметками для монтажёра.",
    },
  ];

  return (
    <section id="placement" className="border-t border-[var(--v7-border)] bg-[var(--v7-dark)] text-[var(--v7-white)]">
      <div className="landing-section">
        <SectionHeading
          dark
          line1="Product placement —"
          line2="отдельный режим."
          subtitle="Не модерация и не юридическая экспертиза. Поиск моментов, где продукт можно встроить нативно — с таймкодами для постпродакшна."
          className="mb-12"
        />
        <div className="landing-grid landing-grid--dark lg:grid-cols-2">
          <div className="landing-cell landing-cell--dark flex flex-col">
            {steps.map((step, i) => (
              <div
                key={step.title}
                className={i > 0 ? "mt-6 border-t border-[var(--v7-border)] pt-6" : ""}
              >
                <p className="landing-kicker text-[var(--v7-text-faint)]">Шаг {i + 1}</p>
                <h3 className="landing-cell-title text-[var(--v7-white-warm)]">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--v7-text-on-dark-secondary)]">
                  {step.text}
                </p>
              </div>
            ))}
            <TryPlacementButton />
          </div>
          <div className="landing-cell landing-cell--dark">
            <PlacementPreview expanded flat />
          </div>
        </div>
      </div>
    </section>
  );
}

function RegulatorySection() {
  const laws = [
    {
      code: "436-ФЗ",
      title: "Защита детей от информации",
      items: [
        "Возрастная маркировка 0+, 6+, 12+, 16+, 18+",
        "Насилие, лексика, алкоголь, наркотики, суицид",
        "Подсказки для редактора: вырезать, заглушить, маркировать",
      ],
    },
    {
      code: "255-ФЗ",
      title: "Иностранные агенты",
      items: [
        "Сигнал при упоминании лиц и организаций",
        "Проверка наличия маркировки в кадре",
        "Сверка имён с реестром иноагентов (Минюст)",
      ],
    },
    {
      code: "114-ФЗ",
      title: "Противодействие экстремизму",
      items: [
        "Запрещённая символика (триаж)",
        "Упоминания организаций — сигнал «проверить»",
        "Сверка с курируемым перечнем, не исчерпывающая",
      ],
    },
  ];

  const registries = [
    {
      title: "Реестр иностранных агентов",
      source: "Минюст РФ",
      check: "Совпадение — сигнал «проверить», не вердикт. Реестр обновляется еженедельно",
    },
    {
      title: "Перечень экстремистских организаций",
      source: "Минюст РФ (курируемое ядро)",
      check: "Частичное совпадение названий — требует ручной сверки с официальным перечнем",
    },
  ];

  return (
    <section id="legal" className="border-t border-[var(--v7-border-light)] bg-[var(--v7-cream-soft)] text-[var(--v7-ink)]">
      <div className="landing-section">
        <SectionHeading
          line1="Нормативная база"
          line2="и реестры."
          subtitle="Категории рисков и подсказки опираются на ключевые нормы РФ. Это ориентиры для редактора — не юридическое заключение."
          className="mb-12"
        />
        <div className="landing-grid lg:grid-cols-3">
          {laws.map((law) => (
            <div key={law.code} className="landing-cell landing-cell--cream">
              <p className="landing-kicker text-[var(--v7-ink-muted)]">{law.code}</p>
              <h3 className="landing-cell-title text-[var(--v7-ink)]">{law.title}</h3>
              <ul className="mt-4 space-y-2">
                {law.items.map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-[var(--v7-text-on-light-muted)]">
                    <ScaleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--v7-ink-muted)]" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="landing-grid mt-px sm:grid-cols-2">
          {registries.map((reg) => (
            <div key={reg.title} className="landing-cell landing-cell--cream">
              <p className="landing-kicker text-[var(--v7-ink-muted)]">Сверка с реестром</p>
              <h3 className="landing-cell-title text-[var(--v7-ink)]">{reg.title}</h3>
              <p className="mt-2 text-sm text-[var(--v7-text-on-light-muted)]">{reg.source}</p>
              <p className="mt-3 text-sm font-medium text-[var(--v7-text-on-light)]">{reg.check}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 rounded-xl border border-[var(--v7-border-light)] bg-[var(--v7-white)] p-6 sm:p-7">
          <p className="text-sm font-medium text-[var(--v7-ink)]">Это не юридическое заключение</p>
          <p className="mt-2 text-sm leading-relaxed text-[var(--v7-text-on-light-muted)]">
            фреймчек проводит автоматический триаж: отмечает потенциально рискованные сцены,
            предлагает возрастной рейтинг и указывает на нормы, которых стоит коснуться. Совпадение
            с реестром — сигнал «проверить», а не подтверждённый статус. Окончательное решение —
            что вырезать, как промаркировать и допускать ли материал к показу — принимает редактор
            или юрист.
          </p>
        </div>
      </div>
    </section>
  );
}

function BentoCard({
  label,
  title,
  children,
  className = "",
  id,
}: {
  label: string;
  title: string;
  children: React.ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <div id={id} className={`landing-cell landing-cell--cream flex flex-col ${className}`}>
      <p className="landing-kicker text-[var(--v7-ink-muted)]">{label}</p>
      <h3 className="landing-cell-title text-[var(--v7-ink)]">{title}</h3>
      <div className="mt-5 flex-1">{children}</div>
    </div>
  );
}

function ReportPreview() {
  const rows = [
    { time: "02:15", cat: "Наркотики", rec: "Вырезать", dot: "bg-red-500" },
    { time: "08:32", cat: "Нецензурная лексика", rec: "Заглушить", dot: "bg-amber-500" },
    { time: "15:10", cat: "Алкоголь", rec: "Маркировать", dot: "bg-blue-500" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between border-b border-[var(--v7-grid-line)] pb-4">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-[var(--v7-ink-muted)]" />
          <span className="text-sm font-medium text-[var(--v7-text-on-light)]">Фильм_пример_2024.mp4</span>
        </div>
        <span className="border border-[var(--v7-border-light)] px-2 py-0.5 text-[11px] font-medium text-[var(--v7-text-on-light-muted)]">
          16+ рекомендуется
        </span>
      </div>
      <div className="mt-1">
        {rows.map((r) => (
          <div key={r.time} className="landing-row">
            <span className="w-10 shrink-0 text-[var(--v7-ink-muted)]">{r.time}</span>
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${r.dot}`} />
            <span className="min-w-0 flex-1 text-[var(--v7-text-on-light)]">{r.cat}</span>
            <span className="shrink-0 text-[var(--v7-ink-muted)]">{r.rec}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlacementPreview({
  expanded = false,
  flat = false,
}: {
  expanded?: boolean;
  flat?: boolean;
}) {
  const VISIBILITY: Record<string, string> = {
    prominent: "Крупный план",
    background: "Фон",
    partial: "Частично",
    unclear: "Неясно",
  };
  const SLOT: Record<string, string> = {
    replace: "Замена предмета",
    opportunity: "Слот в сцене",
  };
  const SUITABILITY: Record<string, string> = {
    high: "Высокая",
    medium: "Средняя",
    low: "Низкая",
  };

  const hits = [
    {
      num: 1,
      start: "00:12",
      end: "00:18",
      description: "Герой за столом в кафе",
      objectDetail: "Стеклянная ёмкость на столе",
      slotType: "replace",
      visibility: "prominent",
      suitability: "high",
      editorNote: "Статичный план, предмет не двигается",
      dot: "bg-emerald-500",
    },
    {
      num: 2,
      start: "01:04",
      end: "01:09",
      description: "Герой сидит в кресле",
      objectDetail: "Свободная рука на подлокотнике",
      slotType: "opportunity",
      visibility: "partial",
      suitability: "medium",
      editorNote: "Короткий план, возможна вставка в руку",
      dot: "bg-amber-500",
    },
    ...(expanded
      ? [
          {
            num: 3,
            start: "02:31",
            end: "02:38",
            description: "Персонаж открывает холодильник",
            objectDetail: "Полка с напитками, контекст кухни",
            slotType: "opportunity",
            visibility: "background",
            suitability: "high",
            editorNote: "Естественный контекст для напитка",
            dot: "bg-emerald-500",
          },
        ]
      : []),
  ];

  const highCount = hits.filter((h) => h.suitability === "high").length;
  const shellClass = flat
    ? "text-left"
    : "rounded-xl border border-[var(--v7-border)] bg-[var(--v7-black)] p-5 text-left sm:p-6";

  return (
    <div className={shellClass}>
      <div className="border-b border-[var(--v7-border)] pb-4">
        <p className="landing-kicker text-[var(--v7-text-faint)]">Product placement</p>
        <p className="mt-1 text-lg font-medium text-[var(--v7-white-warm)]">«энергетический напиток»</p>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
          <span className="text-[var(--v7-text-on-dark-secondary)]">
            Слотов:{" "}
            <span className="font-medium tabular-nums text-[var(--v7-white-warm)]">{hits.length}</span>
          </span>
          <span className="text-[var(--v7-text-on-dark-secondary)]">
            Высокая пригодность:{" "}
            <span className="font-medium tabular-nums text-[var(--v7-white-warm)]">{highCount}</span>
          </span>
        </div>
      </div>

      {!flat && (
        <p className="mt-4 text-sm leading-relaxed text-[var(--v7-text-on-dark-secondary)]">
          Места для размещения — откройте свой файл и перемотайте по таймкоду.
        </p>
      )}

      <div className={flat ? "mt-4" : "mt-5"}>
        <p className="mb-3 text-left text-sm font-medium text-[var(--v7-white-warm)]">
          Места для размещения ({hits.length})
        </p>
        {hits.map((hit) => (
          <div key={hit.num} className="landing-hit">
            <div className="landing-hit-meta mb-2">
              <span className="text-[var(--v7-text-faint)]">#{hit.num}</span>
              <span className="font-mono text-[var(--v7-text-muted)]">
                {hit.start} – {hit.end}
              </span>
              <span className="inline-flex items-center gap-1.5 text-[var(--v7-orange-soft)]">
                <span className={`h-1.5 w-1.5 rounded-full ${hit.dot}`} />
                {SUITABILITY[hit.suitability]}
              </span>
            </div>
            <p className="mb-3 text-left text-sm text-[var(--v7-white-warm)]">{hit.description}</p>
            <dl className="landing-hit-field space-y-1.5">
              <dt>В кадре</dt>
              <dd>{hit.objectDetail}</dd>
              <dt>Заметность</dt>
              <dd>{VISIBILITY[hit.visibility]}</dd>
              <dt>Тип слота</dt>
              <dd>{SLOT[hit.slotType]}</dd>
              <dt>Для монтажа</dt>
              <dd>{hit.editorNote}</dd>
            </dl>
          </div>
        ))}
      </div>
    </div>
  );
}

function SocialProof() {
  const quotes = [
    {
      metric: "×50",
      label: "быстрее ручной проверки",
      text: "Час видео анализируется за минуты. Эксперт получает готовый список проблемных фрагментов с таймкодами — и тратит время только на сложные случаи.",
      author: "Продакшн-студия",
      role: "Постпродакшн",
    },
    {
      metric: "−90%",
      label: "стоимости первичной проверки",
      text: "Пакетная проверка каталога перед публикацией стала предсказуемой по срокам и бюджету. Фиксированная цена за час видео вместо ставки эксперта.",
      author: "Онлайн-кинотеатр",
      role: "Контент-отдел",
    },
  ];

  const comparisons = [
    {
      name: "Проверка 1 часа видео",
      before: "3–5 часов",
      with: "5–20 минут",
      result: "в разы быстрее",
    },
    {
      name: "Стоимость 1 часа",
      before: "8 000 – 15 000 ₽",
      with: "от 600 ₽",
      result: "до −92%",
    },
    {
      name: "Категории риска",
      before: "По чек-листу",
      with: "18+ автоматически",
      result: "стабильно",
    },
    {
      name: "Product placement",
      before: "Ручной просмотр",
      with: "Слоты с таймкодами",
      result: "для монтажа",
    },
  ];

  return (
    <section id="proof" className="bg-[var(--v7-cream-soft)] text-[var(--v7-ink)]">
      <div className="mx-auto max-w-6xl px-6 pb-20 sm:pb-24">
        <div className="grid gap-px border border-[var(--v7-border-light)] bg-[var(--v7-grid-line)] sm:grid-cols-2">
          {quotes.map((q) => (
            <div key={q.author} className="bg-[var(--v7-cream-soft)] p-8 sm:p-10">
              <div className="mb-6">
                <div className="text-4xl font-medium tracking-[-0.03em] text-[var(--v7-ink)]">
                  {q.metric}
                </div>
                <div className="mt-1 text-xs text-[var(--v7-ink-muted)]">{q.label}</div>
              </div>
              <p className="text-lg font-normal leading-[1.65] text-[var(--v7-ink)]">{q.text}</p>
              <div className="mt-6 space-y-3 text-sm">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.12em] text-[var(--v7-ink-muted)]">
                    Тип компании
                  </div>
                  <div className="mt-0.5 font-medium text-[var(--v7-text-on-light)]">{q.author}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.12em] text-[var(--v7-ink-muted)]">
                    Отдел
                  </div>
                  <div className="mt-0.5 text-[var(--v7-text-on-light-muted)]">{q.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-px overflow-hidden border border-[var(--v7-border-light)] bg-[var(--v7-surface)]">
          <div className="grid grid-cols-4 border-b border-[var(--v7-grid-line)] text-[11px] uppercase tracking-wider text-[var(--v7-ink-muted)]">
            <div className="p-4 sm:p-5" />
            <div className="p-4 text-center sm:p-5">До</div>
            <div className="p-4 text-center sm:p-5">с фреймчек</div>
            <div className="p-4 text-center sm:p-5">Результат</div>
          </div>
          {comparisons.map((row, i) => (
            <div
              key={row.name}
              className={`grid grid-cols-4 text-sm ${
                i < comparisons.length - 1 ? "border-b border-[var(--v7-surface-muted)]" : ""
              }`}
            >
              <div className="p-4 font-medium text-[var(--v7-text-on-light)] sm:p-5">{row.name}</div>
              <div className="p-4 text-center text-[var(--v7-text-on-light-muted)] sm:p-5">{row.before}</div>
              <div className="p-4 text-center text-[var(--v7-text-on-light)] sm:p-5">{row.with}</div>
              <div className="p-4 text-center font-medium text-[var(--v7-orange)] sm:p-5">
                {row.result}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  const plans = [
    {
      name: "Старт",
      price: "600",
      unit: "за 1 час видео",
      description: "Для разовых проверок",
      features: ["До 5 ч/мес", "Модерация + placement", "Отчёт Word"],
    },
    {
      name: "Бизнес",
      price: "480",
      unit: "за 1 час видео",
      description: "Для регулярной работы",
      features: ["До 50 ч/мес", "Приоритет", "Проекты и папки"],
      highlighted: true,
    },
    {
      name: "Корпоративный",
      price: "По запросу",
      unit: "",
      description: "Для крупных объёмов",
      features: ["Без лимита", "API", "SLA и поддержка"],
    },
  ];

  return (
    <section id="pricing" className="bg-[var(--v7-white)] text-[var(--v7-ink)]">
      <div className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <SectionHeading
          line1="Прозрачная"
          line2="стоимость."
          subtitle="Оплата за объём видео. Первичная проверка перед финальной экспертизой."
          className="mb-12"
        />
        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((plan) => {
            const highlighted = plan.highlighted;
            return (
            <div
              key={plan.name}
              className={`flex flex-col rounded-2xl border p-7 ${
                highlighted
                  ? "border-[var(--v7-ink)] bg-[var(--v7-dark)] text-[var(--v7-white)]"
                  : "border-[var(--v7-border-light)] bg-[var(--v7-cream-soft)] text-[var(--v7-ink)]"
              }`}
            >
              <div className={`text-sm ${highlighted ? "text-[var(--v7-text-muted)]" : "text-[var(--v7-text-on-light-muted)]"}`}>
                {plan.name}
              </div>
              <div className="mt-3 text-4xl font-medium tracking-[-0.03em]">
                {plan.price.match(/^\d/) ? (
                  <>
                    {plan.price}
                    <span className={`text-lg font-normal ${highlighted ? "text-[var(--v7-text-muted)]" : "text-[var(--v7-ink-muted)]"}`}> ₽</span>
                  </>
                ) : (
                  plan.price
                )}
              </div>
              {plan.unit ? (
                <div className={`mt-1 text-sm ${highlighted ? "text-[var(--v7-text-muted)]" : "text-[var(--v7-text-on-light-muted)]"}`}>
                  {plan.unit}
                </div>
              ) : null}
              <p className={`mt-3 text-sm ${highlighted ? "text-[var(--v7-text-subtle)]" : "text-[var(--v7-text-on-light-muted)]"}`}>
                {plan.description}
              </p>
              <ul className="mt-6 flex-1 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className={`flex items-center gap-2 text-sm ${highlighted ? "text-[var(--v7-white-warm)]" : "text-[var(--v7-text-on-light)]"}`}>
                    <CheckCircle2 className={`h-3.5 w-3.5 shrink-0 ${highlighted ? "text-[var(--v7-text-muted)]" : "text-[var(--v7-ink-muted)]"}`} />
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href="#cta"
                className={`mt-8 block rounded-full py-3 text-center text-sm font-medium transition-colors ${
                  highlighted
                    ? "bg-[var(--v7-white)] text-[var(--v7-ink)] hover:bg-[var(--v7-cream)]"
                    : "bg-[var(--v7-dark)] text-[var(--v7-white)] hover:bg-[var(--v7-dark-elevated)]"
                }`}
              >
                Оставить заявку
              </a>
            </div>
          );
          })}
        </div>
      </div>
    </section>
  );
}

function Security() {
  const items = [
    { icon: Lock, title: "Контент не передаётся третьим лицам" },
    { icon: Server, title: "Изолированная инфраструктура" },
    { icon: Trash2, title: "Удаление данных по запросу" },
    { icon: Eye, title: "Работа с закрытым контентом и NDA" },
  ];

  return (
    <section className="border-t border-[var(--v7-border-light)] bg-[var(--v7-cream)] text-[var(--v7-ink)]">
      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-16 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <div key={item.title}>
            <item.icon className="mb-3 h-4 w-4 text-[var(--v7-ink-muted)]" strokeWidth={1.5} />
            <p className="text-sm text-[var(--v7-text-on-light)]">{item.title}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ClosingCTA() {
  return (
    <section id="cta" className="bg-[var(--v7-black)] text-[var(--v7-white)]">
      <div className="landing-section">
        <div className="landing-cta-grid">
          <div>
            <h2 className="landing-display-lg font-normal">
              <span className="text-[var(--v7-text-muted)]">Загрузите раз.</span>
              <br />
              <span className="text-[var(--v7-text-muted)]">Проверяйте весь каталог.</span>
              <br />
              <span className="font-medium text-[var(--v7-white)]">Улучшайте процесс.</span>
            </h2>
            <p className="mt-6 max-w-md text-[var(--landing-body)] text-[var(--v7-text-subtle)]">
              Оставьте контакты — подберём тариф и покажем работу на вашем видео.
            </p>
          </div>
          <div>
            <p className="landing-kicker mb-6 text-[var(--v7-text-faint)]">Связаться</p>
            <ContactForm />
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  const columns = [
    {
      title: "Продукт",
      links: [
        { label: "Сценарии", href: "#workflows" },
        { label: "Платформа", href: "#platform" },
        { label: "Категории", href: "#categories" },
        { label: "Product placement", href: "#placement" },
        { label: "Нормативная база", href: "#legal" },
        { label: "Стоимость", href: "#pricing" },
      ],
    },
    {
      title: "Законодательство",
      links: [
        { label: "436-ФЗ", href: "https://www.consultant.ru/document/cons_doc_LAW_108808/" },
        { label: "255-ФЗ", href: "https://www.consultant.ru/document/cons_doc_LAW_421788/" },
        { label: "114-ФЗ", href: "https://www.consultant.ru/document/cons_doc_LAW_37867/" },
      ],
    },
    {
      title: "Компания",
      links: [
        { label: "Войти", href: "#login" },
        { label: "Регистрация", href: "/register" },
        { label: "Помощь", href: "/help" },
      ],
    },
  ];

  return (
    <footer className="border-t border-[var(--v7-border)] bg-[var(--v7-dark)] text-[var(--v7-white)]">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-12 lg:grid-cols-[1.2fr_2fr]">
          <div>
            <Logo light />
            <h3 className="mt-6 text-2xl font-medium leading-snug tracking-tight text-[var(--v7-white)] sm:text-3xl">
              AI-анализ
              <br />
              <span className="text-[var(--v7-text-muted)]">видеоконтента</span>
              <br />
              для медиа.
            </h3>
            <a
              href="#cta"
              className="mt-8 inline-flex rounded-full bg-[var(--v7-white)] px-5 py-2.5 text-sm font-medium text-[var(--v7-ink)] transition-colors hover:bg-[var(--v7-cream)]"
            >
              Оставить заявку
            </a>
          </div>
          <div className="grid gap-8 sm:grid-cols-3">
            {columns.map((col) => (
              <div key={col.title}>
                <p className="mb-4 text-[11px] uppercase tracking-[0.14em] text-[var(--v7-text-faint)]">
                  {col.title}
                </p>
                <ul className="space-y-2.5">
                  {col.links.map((link) => (
                    <li key={link.label}>
                      {link.label === "Войти" ? (
                        <FooterLoginLink />
                      ) : link.label === "Регистрация" ? (
                        <FooterRegisterLink />
                      ) : "href" in link && link.href.startsWith("http") ? (
                        <a
                          href={link.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-[var(--v7-text-subtle)] transition-colors hover:text-[var(--v7-white-warm)]"
                        >
                          {link.label}
                        </a>
                      ) : (
                        <a
                          href={link.href}
                          className="text-sm text-[var(--v7-text-subtle)] transition-colors hover:text-[var(--v7-white-warm)]"
                        >
                          {link.label}
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-12 flex flex-col gap-3 border-t border-[var(--v7-border)] pt-8 text-sm text-[var(--v7-text-faint)] sm:flex-row sm:items-center sm:justify-between">
          <span>© {new Date().getFullYear()} фреймчек</span>
          <a href="mailto:info@фреймчек.рф" className="transition-colors hover:text-[var(--v7-text-muted)]">
            info@фреймчек.рф
          </a>
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  const sections = [
    WorkflowGrid,
    PlatformSection,
    CategoriesSection,
    ProductPlacementSection,
    RegulatorySection,
    SocialProof,
    Pricing,
    Security,
    ClosingCTA,
  ];

  return (
    <LandingLoginHost>
      <div className="landing-page min-h-screen bg-[var(--v7-black)] font-sans text-[var(--v7-white)]">
        <LandingNav />
        <Hero />
        {sections.map((Section, i) => (
          <Reveal key={i}>
            <Section />
          </Reveal>
        ))}
        <Footer />
      </div>
    </LandingLoginHost>
  );
}
