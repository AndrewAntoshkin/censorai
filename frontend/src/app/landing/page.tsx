import type { Metadata } from "next";
import Image from "next/image";
import {
  Upload,
  Brain,
  FileText,
  Zap,
  Shield,
  CheckCircle2,
  X,
  Play,
  ArrowRight,
  ChevronRight,
  Building2,
  Tv,
  Film,
  Archive,
  Send,
  Lock,
  Server,
  Trash2,
  Eye,
  Layers,
  ListChecks,
  Filter,
  ExternalLink,
  Scale as ScaleIcon,
} from "lucide-react";
import { ContactForm } from "@/components/landing/contact-form";
import { Reveal } from "@/components/landing/reveal";

export const metadata: Metadata = {
  title: "фреймчек — AI-анализ видеоконтента",
  description:
    "Автоматическая проверка видео на соответствие требованиям законодательства РФ. Быстрее, точнее и дешевле ручной работы.",
};

function Logo() {
  return (
    <Image
      src="/logo.png"
      alt="фреймчек"
      width={98}
      height={20}
      className="h-5 w-auto"
      priority
    />
  );
}

function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-neutral-200/70">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Logo />
        <div className="hidden md:flex items-center gap-8 text-sm text-neutral-500">
          <a href="#audience" className="hover:text-neutral-900 transition-colors">
            Кому подходит
          </a>
          <a href="#how" className="hover:text-neutral-900 transition-colors">
            Как работает
          </a>
          <a
            href="#comparison"
            className="hover:text-neutral-900 transition-colors"
          >
            Сравнение
          </a>
          <a href="#pricing" className="hover:text-neutral-900 transition-colors">
            Стоимость
          </a>
          <a href="#security" className="hover:text-neutral-900 transition-colors">
            Безопасность
          </a>
        </div>
        <a
          href="#cta"
          className="bg-[#0048ff] text-white text-sm px-5 py-2 rounded-full hover:bg-[#0036cc] transition-colors"
        >
          Оставить заявку
        </a>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section className="pt-36 pb-20 px-6">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-x-12 gap-y-14 items-center">
        <div>
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#f0f3ff] text-[11px] font-mono uppercase tracking-[0.12em] text-[#0048ff] mb-7">
            <Zap className="w-3.5 h-3.5" />
            Час видео за ~5 минут
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-[3.5rem] font-normal tracking-[-0.02em] text-neutral-900 leading-[1.08]">
            Проверка видео
            <br />
            на&nbsp;соответствие{" "}
            <span className="text-[#0048ff]">законодательству&nbsp;РФ</span>
          </h1>
          <p className="mt-6 text-lg text-neutral-500 max-w-xl leading-relaxed">
            Покадровый AI-анализ: риски по сценам с&nbsp;таймкодами, возрастной
            рейтинг и&nbsp;сверка с&nbsp;реестрами Минюста. Первичная проверка
            перед финальной экспертизой — быстрее, точнее и&nbsp;дешевле ручной
            работы.
          </p>
          <div className="mt-9 flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <a
              href="#cta"
              className="inline-flex items-center gap-2 bg-[#0048ff] text-white px-7 py-3.5 rounded-full text-sm font-medium hover:bg-[#0036cc] transition-colors"
            >
              Оставить заявку
              <ArrowRight className="w-4 h-4" />
            </a>
            <a
              href="#how"
              className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 transition-colors"
            >
              Как это работает
              <ChevronRight className="w-4 h-4" />
            </a>
          </div>
          <p className="mt-6 text-xs text-neutral-400 max-w-md">
            Сервис не заменяет юридическую экспертизу, а&nbsp;ускоряет поиск
            потенциально проблемных фрагментов
          </p>
        </div>

        <HeroPreview />
      </div>
    </section>
  );
}

function HeroPreview() {
  const rows = [
    { time: "02:15", dot: "bg-red-500", cat: "Наркотики", rec: "Вырезать" },
    { time: "08:32", dot: "bg-amber-500", cat: "Нецензурная лексика", rec: "Заглушить" },
    { time: "15:10", dot: "bg-[#0048ff]", cat: "Алкоголь", rec: "Маркировать" },
  ];

  return (
    <div className="relative lg:pl-6">
      <div className="absolute -inset-3 sm:-inset-5 bg-[#f0f3ff] rounded-[2rem] -z-10 hidden lg:block" />
      <div className="bg-white rounded-2xl border border-neutral-200/70 p-5 shadow-[0_30px_70px_-35px_rgba(28,25,23,0.30)]">
        <div className="flex items-center justify-between gap-3 pb-4 border-b border-neutral-100">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-4 h-4 text-neutral-400 shrink-0" />
            <span className="text-sm font-medium text-neutral-700 truncate">
              Фильм_пример_2024.mp4
            </span>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#f0f3ff] text-[#0048ff] font-medium shrink-0">
            16+ рекомендуется
          </span>
        </div>

        <div className="mt-4 space-y-3">
          {rows.map((r) => (
            <div key={r.time} className="flex items-center gap-3 text-xs">
              <span className="font-mono text-neutral-400 shrink-0 w-10">
                {r.time}
              </span>
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${r.dot}`} />
              <span className="text-neutral-700 flex-1 truncate">{r.cat}</span>
              <span className="text-neutral-400 shrink-0">{r.rec}</span>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-neutral-100 flex items-center gap-2.5">
          <ScaleIcon className="w-4 h-4 text-[#0048ff] shrink-0" />
          <span className="text-xs text-neutral-500">
            Реестр Минюста:{" "}
            <span className="text-neutral-800 font-medium">1 совпадение</span>{" "}
            (иноагенты)
          </span>
        </div>
      </div>
    </div>
  );
}

function Stats() {
  const stats = [
    { value: "~5 мин", label: "на час видео" },
    { value: "18+", label: "категорий проверки" },
    { value: "24/7", label: "без выходных" },
    { value: "×50", label: "быстрее человека" },
  ];

  return (
    <section className="pb-24 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="p-6 rounded-2xl bg-white border border-neutral-200/70"
            >
              <div className="text-2xl sm:text-3xl font-semibold text-neutral-900">
                {stat.value}
              </div>
              <div className="mt-1 text-sm text-neutral-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function TargetAudience() {
  const audiences = [
    {
      icon: Tv,
      title: "ТВ-каналы",
      description: "Проверка эфирного контента перед выходом в сетку вещания",
    },
    {
      icon: Play,
      title: "Онлайн-кинотеатры",
      description: "Анализ каталога перед загрузкой на платформу",
    },
    {
      icon: Film,
      title: "Продакшн-студии",
      description:
        "Контроль контента на этапе постпродакшена до сдачи заказчику",
    },
    {
      icon: Send,
      title: "Дистрибьюторы контента",
      description:
        "Проверка закупленного контента перед перепродажей и лицензированием",
    },
    {
      icon: Archive,
      title: "Архивы и медиабиблиотеки",
      description:
        "Массовый анализ архивного фонда для классификации и маркировки",
    },
    {
      icon: Building2,
      title: "Рекламные агентства",
      description:
        "Проверка рекламных роликов на соответствие требованиям площадок",
    },
  ];

  return (
    <section id="audience" className="py-24 px-6 bg-neutral-50">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Для кого
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Кому подходит
          </h2>
          <p className="mt-4 text-neutral-500">
            Для компаний, которые работают с видеоконтентом и&nbsp;несут
            ответственность за его соответствие законодательству
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {audiences.map((item) => (
            <div
              key={item.title}
              className="bg-white rounded-2xl p-6 border border-neutral-200/70 flex gap-4"
            >
              <div className="w-10 h-10 rounded-xl bg-[#f0f3ff] text-[#0048ff] flex items-center justify-center shrink-0">
                <item.icon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-medium text-neutral-900 mb-1">
                  {item.title}
                </h3>
                <p className="text-sm text-neutral-500 leading-relaxed">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      icon: Upload,
      title: "Загрузите видео",
      description:
        "Перетащите файл или укажите ссылку. Поддерживаются MP4, MOV, AVI, MKV, WMV, WebM — до 500 МБ на файл. Пакетная и параллельная загрузка.",
    },
    {
      icon: Brain,
      title: "AI анализирует сцены",
      description:
        "Покадрово разбиваем видео на сцены и проверяем каждую по 18+ категориям с уровнем риска, рекомендуем возрастной рейтинг (436-ФЗ) и извлекаем имена и организации для сверки.",
    },
    {
      icon: FileText,
      title: "Получите отчёт",
      description:
        "Детальный отчёт с таймкодами, цитатами и рекомендациями (вырезать / заглушить / размыть / маркировать), возрастным рейтингом и сверкой с реестрами Минюста. Выгрузка в Word (.docx).",
    },
  ];

  return (
    <section id="how" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Процесс
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Три шага до результата
          </h2>
          <p className="mt-4 text-neutral-500">
            Весь процесс занимает несколько минут — от загрузки до готового
            отчёта
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <div key={step.title} className="relative">
              <div className="bg-white rounded-2xl p-8 h-full border border-neutral-200/70">
                <div className="w-10 h-10 rounded-xl bg-[#0048ff] text-white flex items-center justify-center text-sm font-medium mb-6">
                  {i + 1}
                </div>
                <h3 className="text-lg font-medium text-neutral-900 mb-3">
                  {step.title}
                </h3>
                <p className="text-sm text-neutral-500 leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function UseCases() {
  const cases = [
    {
      icon: Eye,
      title: "Проверка перед выпуском в эфир",
      description:
        "Быстрый скрининг готового выпуска или серии перед размещением в сетке вещания или на платформе",
    },
    {
      icon: Layers,
      title: "Анализ каталога при загрузке",
      description:
        "Пакетная проверка библиотеки контента перед публикацией на стриминговой платформе или в архиве",
    },
    {
      icon: ListChecks,
      title: "Контроль контента от подрядчиков",
      description:
        "Автоматическая проверка материалов, поступающих от внешних продакшенов и поставщиков",
    },
    {
      icon: Filter,
      title: "Первичная фильтрация перед экспертизой",
      description:
        "Предварительный отсев проблемного контента, чтобы эксперт сфокусировался на действительно сложных случаях",
    },
  ];

  return (
    <section className="py-24 px-6 bg-neutral-50">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Сценарии
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Как использовать в работе
          </h2>
          <p className="mt-4 text-neutral-500">
            фреймчек встраивается в&nbsp;существующие процессы компании
            как&nbsp;этап автоматической предварительной проверки
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-6">
          {cases.map((item) => (
            <div
              key={item.title}
              className="bg-white rounded-2xl p-8 border border-neutral-200/70"
            >
              <div className="w-10 h-10 rounded-xl bg-[#f0f3ff] text-[#0048ff] flex items-center justify-center mb-5">
                <item.icon className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-medium text-neutral-900 mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-neutral-500 leading-relaxed">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RiskCategories() {
  const categories = [
    { name: "Наркотики", tip: "Демонстрация, употребление, инструкции или пропаганда наркотических веществ" },
    { name: "Оружие", tip: "Показ оружия, инструкции по изготовлению или применению" },
    { name: "Насилие и кровь", tip: "Сцены физического насилия, избиений, пыток, кровь" },
    { name: "Чрезмерная жестокость", tip: "Натуралистичные сцены жестокости и расчленения" },
    { name: "Сексуальный контент", tip: "Откровенные сцены, порнография, эротика" },
    { name: "Нецензурная лексика", tip: "Мат и обсценные выражения в репликах и тексте" },
    { name: "Противоправные действия", tip: "Демонстрация и инструкции по совершению правонарушений" },
    { name: "Героизация преступлений", tip: "Романтизация и оправдание преступной деятельности" },
    { name: "Алкоголь", tip: "Демонстрация или пропаганда употребления алкоголя" },
    { name: "Курение", tip: "Демонстрация или пропаганда табака и курения" },
    { name: "Жестокость к животным", tip: "Сцены насилия и жестокого обращения с животными" },
    { name: "Запрещённая символика", tip: "Экстремистская и иная запрещённая символика в кадре" },
    { name: "Дискредитация ценностей", tip: "В т.ч. дискредитация ВС РФ и государственных институтов" },
    { name: "Пропаганда", tip: "Пропаганда запрещённых идей, веществ и действий" },
    { name: "Пропаганда ЛГБТ", tip: "Пропаганда нетрадиционных отношений (КоАП 6.21)" },
    { name: "Суицид и самоповреждение", tip: "Описание способов и пропаганда суицида (436-ФЗ)" },
    { name: "Педофилия", tip: "Оправдание или пропаганда педофилии" },
    { name: "Иноагенты — сверка", tip: "Имена и организации без маркировки сверяются с реестром Минюста (255-ФЗ)" },
    { name: "Опасный текст в кадре", tip: "Запрещённый или важный текст, ссылки, контакты на экране" },
  ];

  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Категории
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Что проверяем
          </h2>
          <p className="mt-4 text-neutral-500">
            Каждая сцена оценивается по всем категориям с уровнем риска —
            критично, возможны проблемы, некритично. Плюс рекомендованный
            возрастной рейтинг и сверка с реестрами Минюста.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {categories.map((cat) => (
            <div
              key={cat.name}
              title={cat.tip}
              className="group relative flex items-center gap-3 px-4 py-3 rounded-2xl bg-white border border-neutral-200/70 hover:bg-[#f0f3ff] hover:border-[#b3c7ff] transition-colors cursor-default"
            >
              <Shield className="w-4 h-4 text-[#1a53ff] shrink-0" />
              <span className="text-sm text-neutral-700">{cat.name}</span>
              <div className="absolute bottom-full left-0 mb-2 px-4 py-2.5 bg-neutral-900 text-white text-xs rounded-lg w-[280px] text-left leading-relaxed opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none z-10">
                {cat.tip}
                <div className="absolute top-full left-6 border-4 border-transparent border-t-neutral-900" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function LegalBasis() {
  const laws = [
    {
      number: "436-ФЗ",
      title:
        "О защите детей от информации, причиняющей вред их здоровью и развитию",
      url: "https://www.consultant.ru/document/cons_doc_LAW_108808/",
      description:
        "Возрастная маркировка, ограничения на контент для несовершеннолетних",
    },
    {
      number: "114-ФЗ",
      title: "О противодействии экстремистской деятельности",
      url: "https://www.consultant.ru/document/cons_doc_LAW_37867/",
      description: "Запрет на распространение экстремистских материалов",
    },
    {
      number: "255-ФЗ",
      title: "О контроле за деятельностью лиц, находящихся под иностранным влиянием",
      url: "https://www.consultant.ru/document/cons_doc_LAW_421788/",
      description:
        "Требования к маркировке материалов иностранных агентов — сверка с реестром Минюста",
    },
    {
      number: "38-ФЗ",
      title: "О рекламе",
      url: "https://www.consultant.ru/document/cons_doc_LAW_58968/",
      description:
        "Требования к рекламному контенту, ограничения на рекламу отдельных товаров",
    },
    {
      number: "149-ФЗ",
      title: "Об информации, информационных технологиях и о защите информации",
      url: "https://www.consultant.ru/document/cons_doc_LAW_61798/",
      description:
        "Общие требования к распространению информации в РФ",
    },
  ];

  return (
    <section className="py-24 px-6 bg-neutral-50">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Законодательство
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Нормативная база
          </h2>
          <p className="mt-4 text-neutral-500">
            Анализ проводится на соответствие ключевым федеральным законам РФ
            в&nbsp;области регулирования контента
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          {laws.map((law) => (
            <a
              key={law.number}
              href={law.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex gap-4 p-5 rounded-2xl bg-white border border-neutral-200/70 hover:border-[#b3c7ff] hover:bg-[#f0f3ff]/30 transition-colors"
            >
              <div className="shrink-0 w-10 h-10 rounded-xl bg-[#dbe5ff] text-[#0048ff] flex items-center justify-center">
                <ScaleIcon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-neutral-900">
                    {law.number}
                  </span>
                  <ExternalLink className="w-3.5 h-3.5 text-neutral-300 group-hover:text-[#1a53ff] transition-colors" />
                </div>
                <p className="text-sm text-neutral-700 leading-snug mb-1">
                  {law.title}
                </p>
                <p className="text-xs text-neutral-400">{law.description}</p>
              </div>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function Comparison() {
  const rows = [
    { feature: "Время на 1 час видео", manual: "3–5 часов", ai: "~5 минут" },
    {
      feature: "Стоимость за 1 час видео",
      manual: "8 000 – 15 000 ₽",
      ai: "от 600 ₽",
    },
    {
      feature: "Единообразие оценки",
      manual: "Зависит от эксперта",
      ai: "Стабильный результат",
    },
    {
      feature: "Количество категорий",
      manual: "Зависит от чек-листа",
      ai: "18+ автоматически",
    },
    {
      feature: "Детализация отчёта",
      manual: "Произвольный формат",
      ai: "Структурированный с таймкодами",
    },
    {
      feature: "Масштабируемость",
      manual: "Ограничена штатом",
      ai: "Без ограничений",
    },
    {
      feature: "Работа 24/7",
      manualBool: false,
      aiBool: true,
      manual: "",
      ai: "",
    },
    {
      feature: "Субъективность",
      manualBool: true,
      aiBool: false,
      manual: "",
      ai: "",
    },
  ];

  return (
    <section id="comparison" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Сравнение
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Ручная работа vs фреймчек
          </h2>
          <p className="mt-4 text-neutral-500">
            Сравните трудозатраты и стоимость традиционного подхода
            с&nbsp;AI-анализом
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-neutral-200/70 overflow-hidden">
          <div className="grid grid-cols-3 text-sm font-medium border-b border-neutral-100">
            <div className="p-5 text-neutral-500"></div>
            <div className="p-5 text-center text-neutral-500">Ручная проверка</div>
            <div className="p-5 text-center text-[#0048ff] font-semibold bg-[#f0f3ff]">
              фреймчек
            </div>
          </div>
          {rows.map((row, i) => (
            <div
              key={row.feature}
              className={`grid grid-cols-3 text-sm ${i < rows.length - 1 ? "border-b border-neutral-50" : ""}`}
            >
              <div className="p-5 text-neutral-700 font-medium">
                {row.feature}
              </div>
              <div className="p-5 text-center text-neutral-500">
                {row.manualBool !== undefined ? (
                  row.manualBool ? (
                    <CheckCircle2 className="w-5 h-5 text-red-400 mx-auto" />
                  ) : (
                    <X className="w-5 h-5 text-green-500 mx-auto" />
                  )
                ) : (
                  row.manual
                )}
              </div>
              <div className="p-5 text-center text-neutral-900 bg-[#f0f3ff]/50 font-medium">
                {row.aiBool !== undefined ? (
                  row.aiBool ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500 mx-auto" />
                  ) : (
                    <X className="w-5 h-5 text-neutral-300 mx-auto" />
                  )
                ) : (
                  row.ai
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ScaleSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="bg-gradient-to-br from-neutral-900 to-neutral-800 rounded-[2rem] p-10 sm:p-14">
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-normal text-white tracking-tight">
                Подходит для больших
                <br />
                объёмов контента
              </h2>
              <p className="mt-4 text-neutral-400 leading-relaxed">
                фреймчек спроектирован для обработки масштабных библиотек
                видеоконтента. Загружайте десятки и сотни часов — система
                справится.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { value: "100+", label: "часов видео в сутки" },
                { value: "24/7", label: "без перерывов" },
                { value: "∞", label: "пакетная загрузка" },
                { value: "API", label: "для интеграций" },
              ].map((item) => (
                <div
                  key={item.label}
                  className="bg-white/5 backdrop-blur rounded-2xl p-5 text-center border border-white/10"
                >
                  <div className="text-2xl font-semibold text-white">
                    {item.value}
                  </div>
                  <div className="mt-1 text-sm text-neutral-400">
                    {item.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  return (
    <section id="pricing" className="py-24 px-6 bg-neutral-50">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Тарифы
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Стоимость
          </h2>
          <p className="mt-4 text-neutral-500">
            Прозрачная оплата за объём видео. Используется как этап первичной
            проверки перед финальной экспертизой.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <PricingCard
            name="Старт"
            price="600"
            unit="за 1 час видео"
            description="Для разовых проверок"
            features={[
              "До 5 часов видео в месяц",
              "Полный анализ по всем категориям",
              "Отчёт в формате Word",
              "Рекомендации по исправлению",
            ]}
          />
          <PricingCard
            name="Бизнес"
            price="480"
            unit="за 1 час видео"
            description="Для регулярной работы"
            features={[
              "До 50 часов видео в месяц",
              "Всё из тарифа Старт",
              "Приоритетная обработка",
              "История анализов",
              "Проекты и папки",
            ]}
            highlighted
          />
          <PricingCard
            name="Корпоративный"
            price="По запросу"
            unit=""
            description="Для крупных объёмов"
            features={[
              "Неограниченный объём",
              "Всё из тарифа Бизнес",
              "API-доступ",
              "Кастомные категории рисков",
              "SLA и выделенная поддержка",
              "Пакетная загрузка и очереди",
            ]}
          />
        </div>
      </div>
    </section>
  );
}

function PricingCard({
  name,
  price,
  unit,
  description,
  features,
  highlighted = false,
}: {
  name: string;
  price: string;
  unit: string;
  description: string;
  features: string[];
  highlighted?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl p-8 flex flex-col ${highlighted ? "bg-neutral-900 text-white ring-2 ring-neutral-900" : "bg-white border border-neutral-200/70"}`}
    >
      <div className="mb-6">
        <h3
          className={`text-sm font-medium mb-4 ${highlighted ? "text-neutral-400" : "text-neutral-500"}`}
        >
          {name}
        </h3>
        <div className="flex items-baseline gap-1">
          {price.match(/^\d/) ? (
            <>
              <span className="text-4xl font-semibold">{price}</span>
              <span
                className={`text-sm ${highlighted ? "text-neutral-400" : "text-neutral-500"}`}
              >
                ₽
              </span>
            </>
          ) : (
            <span className="text-2xl font-semibold">{price}</span>
          )}
        </div>
        {unit && (
          <div
            className={`text-sm mt-1 ${highlighted ? "text-neutral-400" : "text-neutral-500"}`}
          >
            {unit}
          </div>
        )}
        <p
          className={`text-sm mt-3 ${highlighted ? "text-neutral-400" : "text-neutral-500"}`}
        >
          {description}
        </p>
      </div>
      <div className="flex-1">
        <ul className="space-y-3">
          {features.map((f) => (
            <li key={f} className="flex items-start gap-3 text-sm">
              <CheckCircle2
                className={`w-4 h-4 shrink-0 mt-0.5 ${highlighted ? "text-white/60" : "text-neutral-400"}`}
              />
              <span>{f}</span>
            </li>
          ))}
        </ul>
      </div>
      <a
        href="#cta"
        className={`mt-8 block text-center py-3 rounded-full text-sm font-medium transition-colors ${highlighted ? "bg-white text-neutral-900 hover:bg-neutral-100" : "bg-neutral-900 text-white hover:bg-neutral-800"}`}
      >
        Оставить заявку
      </a>
    </div>
  );
}

function Calculator() {
  const examples = [
    {
      title: "Блогер",
      description: "10 роликов по 15 минут в месяц",
      totalHours: 2.5,
      manualCost: "20 000 – 37 500",
      manualTime: "8 – 13 часов",
      aiCost: "1 500",
      aiTime: "~13 минут",
    },
    {
      title: "Продакшн-студия",
      description: "5 фильмов по 1.5 часа в месяц",
      totalHours: 7.5,
      manualCost: "60 000 – 112 500",
      manualTime: "22 – 38 часов",
      aiCost: "3 600",
      aiTime: "~38 минут",
    },
    {
      title: "ТВ-канал",
      description: "30 часов эфира в месяц",
      totalHours: 30,
      manualCost: "240 000 – 450 000",
      manualTime: "90 – 150 часов",
      aiCost: "14 400",
      aiTime: "~2.5 часа",
    },
  ];

  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Экономия
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Примеры расчётов
          </h2>
          <p className="mt-4 text-neutral-500">
            Посмотрите, сколько вы экономите с&nbsp;фреймчеком на реальных
            сценариях
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {examples.map((ex) => (
            <div
              key={ex.title}
              className="bg-white rounded-2xl border border-neutral-200/70 overflow-hidden"
            >
              <div className="p-6 border-b border-neutral-50">
                <div className="flex items-center gap-3 mb-2">
                  <Play className="w-4 h-4 text-neutral-400" />
                  <h3 className="font-medium text-neutral-900">{ex.title}</h3>
                </div>
                <p className="text-sm text-neutral-500">{ex.description}</p>
                <p className="text-xs text-neutral-400 mt-1">
                  Итого: {ex.totalHours} ч видео
                </p>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <div className="text-xs text-neutral-400 uppercase tracking-wider mb-2">
                    Ручная проверка
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-500">Стоимость</span>
                    <span className="text-neutral-700 font-medium">
                      {ex.manualCost} ₽
                    </span>
                  </div>
                  <div className="flex justify-between text-sm mt-1">
                    <span className="text-neutral-500">Время</span>
                    <span className="text-neutral-700">{ex.manualTime}</span>
                  </div>
                </div>

                <div className="border-t border-neutral-50 pt-4">
                  <div className="text-xs text-neutral-400 uppercase tracking-wider mb-2">
                    фреймчек
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-500">Стоимость</span>
                    <span className="text-neutral-900 font-semibold">
                      {ex.aiCost} ₽
                    </span>
                  </div>
                  <div className="flex justify-between text-sm mt-1">
                    <span className="text-neutral-500">Время</span>
                    <span className="text-neutral-900 font-medium">
                      {ex.aiTime}
                    </span>
                  </div>
                </div>

                <div className="bg-green-50 rounded-xl p-3 text-center">
                  <span className="text-green-700 text-sm font-medium">
                    Экономия до{" "}
                    {Math.round(
                      (1 -
                        parseInt(ex.aiCost.replace(/\s/g, "")) /
                          parseInt(
                            ex.manualCost
                              .split("–")[1]
                              ?.trim()
                              .replace(/\s/g, "") ||
                              ex.manualCost.replace(/\s/g, "")
                          )) *
                        100
                    )}
                    %
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 bg-white rounded-2xl border border-neutral-200/70 p-8">
          <h3 className="text-lg font-medium text-neutral-900 mb-4">
            Как считаем
          </h3>
          <div className="grid sm:grid-cols-2 gap-6 text-sm text-neutral-500">
            <div>
              <p className="font-medium text-neutral-700 mb-2">Ручная проверка</p>
              <ul className="space-y-1.5">
                <li>Специалист тратит 3–5 часов на 1 час видео</li>
                <li>Стоимость работы: 8 000 – 15 000 ₽ за час видео</li>
                <li>Зависит от квалификации и региона</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-neutral-700 mb-2">фреймчек</p>
              <ul className="space-y-1.5">
                <li>Обработка 1 часа видео занимает ~5 минут</li>
                <li>Тариф «Бизнес»: 480 ₽ за час видео (8 ₽/мин)</li>
                <li>Фиксированная стоимость, без скрытых платежей</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Report() {
  return (
    <section className="py-24 px-6 bg-neutral-50">
      <div className="max-w-5xl mx-auto">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
              Детальный отчёт
              <br />
              по каждой сцене
            </h2>
            <p className="mt-4 text-neutral-500 leading-relaxed">
              Для каждой сцены — точные таймкоды, описание содержимого, риски с
              уровнем серьёзности и рекомендации: вырезать, сократить, заглушить,
              размыть или маркировать. Плюс возрастной рейтинг и сверка с
              реестрами.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                "Таймкоды, описание сцены, цитаты и текст с экрана",
                "Уровень риска: критично / возможны проблемы / некритично",
                "Рекомендация по каждому риску: вырезать, заглушить, размыть, маркировать",
                "Рекомендованный возрастной рейтинг 0+…18+ (436-ФЗ) с триггерами",
                "Сверка имён и организаций с реестрами Минюста (иноагенты)",
                "Обнаружение уже имеющихся маркировок и дисклеймеров",
                "Выгрузка в Word (.docx), проекты и папки для библиотек",
              ].map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 text-sm text-neutral-600"
                >
                  <CheckCircle2 className="w-4 h-4 text-[#1a53ff] shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-neutral-200/70">
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-neutral-50 rounded-xl p-4 border border-neutral-200/70">
                <div>
                  <div className="text-[11px] text-neutral-400 mb-0.5">
                    Возрастной рейтинг
                  </div>
                  <div className="text-sm font-medium text-neutral-800">
                    16+ рекомендуется
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[11px] text-neutral-400 mb-0.5">
                    Реестр Минюста
                  </div>
                  <div className="text-sm font-medium text-[#0048ff]">
                    1 совпадение
                  </div>
                </div>
              </div>
              <div className="bg-neutral-50 rounded-xl p-5 border border-neutral-200/70">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-neutral-500">
                    Сцена 3 — 02:15 → 02:47
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-600 font-medium">
                    Критический
                  </span>
                </div>
                <p className="text-sm text-neutral-700 mb-3">
                  Персонаж демонстрирует употребление запрещённых веществ в
                  позитивном контексте. На экране отчётливо видны атрибуты.
                </p>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                    Наркотики
                  </span>
                  <span className="text-xs text-neutral-400">→</span>
                  <span className="text-xs text-neutral-500">
                    Рекомендация: удалить сцену
                  </span>
                </div>
              </div>

              <div className="bg-neutral-50 rounded-xl p-5 border border-neutral-200/70">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-neutral-500">
                    Сцена 7 — 08:32 → 08:55
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 font-medium">
                    Предупреждение
                  </span>
                </div>
                <p className="text-sm text-neutral-700 mb-3">
                  Фоновый диалог содержит ненормативную лексику. Визуальный ряд
                  нейтрален.
                </p>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                    Лексика
                  </span>
                  <span className="text-xs text-neutral-400">→</span>
                  <span className="text-xs text-neutral-500">
                    Рекомендация: заглушить аудио
                  </span>
                </div>
              </div>

              <div className="bg-neutral-50 rounded-xl p-5 border border-neutral-200/70">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-neutral-500">
                    Сцена 12 — 15:10 → 15:38
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[#f0f3ff] text-[#0048ff] font-medium">
                    Информационный
                  </span>
                </div>
                <p className="text-sm text-neutral-700 mb-3">
                  Краткое изображение алкогольной продукции на заднем плане.
                  Контекст нейтральный.
                </p>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                    Алкоголь
                  </span>
                  <span className="text-xs text-neutral-400">→</span>
                  <span className="text-xs text-neutral-500">
                    Рекомендация: допустимо
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Security() {
  const items = [
    {
      icon: Lock,
      title: "Видео не передаётся третьим лицам",
      description:
        "Контент обрабатывается исключительно для анализа и не используется для обучения моделей или иных целей",
    },
    {
      icon: Server,
      title: "Защищённая инфраструктура",
      description:
        "Обработка на изолированных серверах с шифрованием данных при передаче и хранении",
    },
    {
      icon: Trash2,
      title: "Удаление данных по запросу",
      description:
        "Вы можете запросить полное удаление загруженных материалов и результатов анализа в любой момент",
    },
    {
      icon: Eye,
      title: "Работа с закрытым контентом",
      description:
        "Поддерживаем работу с невыпущенным и конфиденциальным контентом в рамках NDA",
    },
  ];

  return (
    <section id="security" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-12 max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#0048ff] mb-4">
            Безопасность
          </p>
          <h2 className="text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Безопасность и&nbsp;конфиденциальность
          </h2>
          <p className="mt-4 text-neutral-500">
            Мы понимаем, что вы работаете с ценным и часто ещё не выпущенным
            контентом. Безопасность данных — наш приоритет.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-6">
          {items.map((item) => (
            <div
              key={item.title}
              className="bg-white rounded-2xl p-8 border border-neutral-200/70"
            >
              <div className="w-10 h-10 rounded-xl bg-green-50 text-green-600 flex items-center justify-center mb-5">
                <item.icon className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-medium text-neutral-900 mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-neutral-500 leading-relaxed">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section id="cta" className="py-24 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <div className="bg-neutral-900 rounded-[2rem] p-12 sm:p-16">
          <h2 className="text-3xl sm:text-4xl font-normal text-white tracking-tight">
            Оставить заявку
          </h2>
          <p className="mt-4 text-neutral-400 max-w-md mx-auto mb-8">
            Оставьте контакты — мы свяжемся с вами и подберём оптимальный вариант
            для вашей задачи.
          </p>
          <ContactForm />
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-neutral-100 py-12 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-8 mb-8">
          <div className="flex items-center gap-3">
            <Logo />
            <span className="text-sm text-neutral-400">
              AI-анализ видеоконтента
            </span>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-8 text-sm text-neutral-500">
            <a href="#audience" className="hover:text-neutral-900 transition-colors">Кому подходит</a>
            <a href="#how" className="hover:text-neutral-900 transition-colors">Как работает</a>
            <a href="#pricing" className="hover:text-neutral-900 transition-colors">Стоимость</a>
            <a href="#security" className="hover:text-neutral-900 transition-colors">Безопасность</a>
          </div>
        </div>
        <div className="border-t border-neutral-100 pt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="text-sm text-neutral-400">
            © {new Date().getFullYear()} фреймчек. Все права защищены.
          </div>
          <a
            href="mailto:info@фреймчек.рф"
            className="text-sm text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            info@фреймчек.рф
          </a>
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  const sections = [
    Stats,
    TargetAudience,
    HowItWorks,
    UseCases,
    RiskCategories,
    LegalBasis,
    Comparison,
    ScaleSection,
    Pricing,
    Calculator,
    Report,
    Security,
    CTA,
  ];

  return (
    <div className="min-h-screen bg-white">
      <Nav />
      <Hero />
      {sections.map((Section, i) => (
        <Reveal key={i}>
          <Section />
        </Reveal>
      ))}
      <Footer />
    </div>
  );
}
