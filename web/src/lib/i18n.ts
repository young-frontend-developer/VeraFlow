// UI chrome only. Every sentence ABOUT TAJWEED comes from the server, out of
// content/rules.json — never from here and never from an LLM.
//
// Uzbek uses the proper modifier letter ʻ (U+02BB) in oʻ / gʻ, not an
// apostrophe. Russian is written as Russian, not as a translation of the Uzbek.
// Both are first drafts by a developer and want a native pass before launch.
export type Lang = "uz" | "ru";

const STRINGS = {
  uz: {
    // navigation
    nav_practice: "Mashq",
    nav_library: "Oyatlar",
    nav_log: "Yozuvlar",

    // recitation
    listen: "Qori oʻqishini tinglang",
    record: "Oʻqishni boshlash",
    stop: "Toʻxtatish",
    recording_hint: "Shoshilmang. Tinch va sekin oʻqing.",
    waiting: "Tinglanmoqda",
    waiting_hint: "Bir necha soniya kutib turing.",

    // all clear
    clear_title: "Barakalla",
    clear_body: "Bu oʻqishda xatolik topilmadi.",

    // uncertain
    unsure_title: "Toʻliq baholay olmadik",
    unsure_body:
      "Bu oʻqishni ishonch bilan baholash uchun maʼlumot yetarli boʻlmadi. Ustozingiz bilan birga tekshirib koʻring.",

    // retry
    retry_noisy_title: "Atrof shovqinli",
    retry_noisy_body:
      "Yozuvda tashqi shovqin koʻp boʻlgani uchun oʻqishni aniq eshita olmadik.",
    retry_short_title: "Yozuv juda qisqa",
    retry_short_body: "Oyat toʻliq oʻqilmagan koʻrinadi.",
    retry_long_title: "Yozuv juda uzun",
    retry_long_body: "Faqat shu oyatni oʻqing, keyingisiga oʻtmang.",
    retry_quiet_title: "Ovoz eshitilmadi",
    retry_quiet_body:
      "Yozuvda deyarli ovoz yoʻq. Mikrofonga ruxsat berilganini tekshiring.",
    retry_unclear_title: "Oʻqishni aniq eshita olmadik",
    retry_unclear_body:
      "Oyat toʻliq va tinch oʻqilsa, bahomiz ancha aniq boʻladi. Shoshilmasdan qaytadan oʻqing.",
    retry_tip_full: "Oyatni boshidan oxirigacha oʻqing",
    retry_tip_pause: "Yozishni boshlagach, bir lahza kutib, keyin oʻqing",
    retry_tip_room: "Tinchroq xonaga oʻting",
    retry_tip_close: "Telefonni ogʻzingizga yaqinroq tuting",
    retry_tip_wait: "Deraza yoki fen ovozi tinganini kuting",
    retry_again: "Qayta oʻqish",

    // correction card
    label_heard: "Nimani eshitdik",
    label_fix: "Qanday tuzatish kerak",
    label_drill: "Mashq",
    teacher_note: "Bunga ishonchimiz toʻliq emas — ustozingiz bilan tekshiring.",
    wrong_button: "Bu baho notoʻgʻri",
    wrong_thanks: "Rahmat. Buni koʻrib chiqamiz.",

    // TILAWAH_SHOW_UNREVIEWED — developer diagnostic, never a learner build
    draft_chip: "QORALAMA",
    draft_note: "Bu izohni qori tekshirmagan. Faqat sinov uchun.",
    draft_unauthored: "Bu xato uchun matn umuman yozilmagan. Faqat kod:",
    draft_banner_title: "Tekshirilmagan izohlar koʻrsatilmoqda",
    draft_banner_body:
      "TILAWAH_SHOW_UNREVIEWED yoqilgan: aniqlangan barcha xatolar, jumladan qori tekshirmaganlari ham koʻrsatilmoqda. Bu faqat dasturchi rejimi.",

    // picker — the whole Quran, not a shortlist
    pick_sura: "Sura tanlang",
    search_sura: "Sura nomi yoki raqami",
    no_matches: "Hech narsa topilmadi.",
    pick_ayah: "Oyatni tanlang.",
    pick_segment: "Qaysi qismini oʻqiysiz?",
    ayat_count: "oyat",
    parts: "qism",
    words: "soʻz",
    seconds_short: "s",
    estimate: "Taxminiy davomiylik",
    change_selection: "Boshqa oyat tanlash",

    // library
    library_title: "Oyatlar",
    library_sub: "Mashq qilish uchun oyatni tanlang.",
    level: "Daraja",

    // log
    log_title: "Yozuvlar",
    log_sub: "Oxirgi oʻqishlaringiz.",
    log_empty: "Hali oʻqish yozilmagan.",
    log_clear: "Xatoliksiz",
    log_noted: "Izoh bor",
    log_retry: "Qayta yozilgan",

    // pilot banner
    pilot_title: "Sinov versiyasi",
    pilot_body:
      "Bu dastur hali sinovdan oʻtmoqda. Tajweed boʻyicha izohlar toʻliq tasdiqlanmagan — ustozingiz bilan tekshirib boring.",

    // consent
    consent_title: "Maʼlumotlaringiz",
    consent_body:
      "Oʻqishlaringizni saqlashga ruxsat bersangiz, tarixni koʻrasiz va biz baholash sifatini yaxshilaymiz. Istagan vaqtda oʻchirib tashlashingiz mumkin.",
    consent_toggle: "Oʻqishlarimni saqlashga ruxsat beraman",
    consent_delete: "Barcha maʼlumotlarim oʻchirildi.",

    // first-run consent screen
    consent_gate_title: "Maʼlumotlaringiz sizniki",
    consent_gate_intro:
      "Boshlashdan oldin bir narsani aniq qilib olaylik: nimani saqlashimizni siz hal qilasiz. Hech narsa avtomatik saqlanmaydi.",
    consent_gate_none_title: "Hech narsa saqlanmaydi",
    consent_gate_none_body:
      "Ruxsat bermasangiz, oʻqishingiz baholanadi va darhol unutiladi. Dasturdan toʻliq foydalanaveramiz.",
    consent_attempts_label: "Oʻqishlarim tarixini saqlash",
    consent_attempts_help:
      "Qaysi oyatni oʻqiganingiz va qanday izoh olganingiz saqlanadi. Ovozingiz saqlanmaydi.",
    consent_audio_label: "Ovoz yozuvlarimni saqlash",
    consent_audio_help:
      "Ovozingiz saqlanadi va faqat baholash sifatini yaxshilash uchun ishlatiladi. Bu alohida ruxsat — istamasangiz belgilamang.",
    consent_gate_accept: "Davom etish",
    consent_gate_skip: "Hech narsa saqlamasdan davom etish",
    consent_gate_footer:
      "Fikringizni istagan vaqtda «Yozuvlar» boʻlimida oʻzgartirishingiz mumkin. Oʻchirsangiz, saqlangan hamma narsa haqiqatan oʻchiriladi.",

    // generic
    error_generic: "Xatolik yuz berdi. Qayta urinib koʻring.",
    loading: "Yuklanmoqda",
  },

  ru: {
    nav_practice: "Практика",
    nav_library: "Аяты",
    nav_log: "Записи",

    listen: "Послушайте чтеца",
    record: "Начать чтение",
    stop: "Остановить",
    recording_hint: "Не торопитесь. Читайте спокойно.",
    waiting: "Слушаем",
    waiting_hint: "Это займёт несколько секунд.",

    clear_title: "Прекрасно",
    clear_body: "В этом чтении ошибок не найдено.",

    unsure_title: "Не смогли оценить полностью",
    unsure_body:
      "Данных не хватило, чтобы оценить это чтение уверенно. Проверьте вместе с вашим устозом.",

    retry_noisy_title: "Вокруг шумно",
    retry_noisy_body:
      "В записи много постороннего шума, и мы не расслышали чтение отчётливо.",
    retry_short_title: "Запись слишком короткая",
    retry_short_body: "Похоже, аят прочитан не полностью.",
    retry_long_title: "Запись слишком длинная",
    retry_long_body: "Прочитайте только этот аят, не переходя к следующему.",
    retry_quiet_title: "Звук не слышен",
    retry_quiet_body:
      "В записи почти нет звука. Проверьте, разрешён ли доступ к микрофону.",
    retry_unclear_title: "Не расслышали чтение отчётливо",
    retry_unclear_body:
      "Если прочитать аят полностью и спокойно, оценка будет намного точнее. Не торопитесь и прочитайте ещё раз.",
    retry_tip_full: "Прочитайте аят от начала до конца",
    retry_tip_pause: "Начав запись, выждите мгновение и затем читайте",
    retry_tip_room: "Перейдите в тихую комнату",
    retry_tip_close: "Держите телефон ближе ко рту",
    retry_tip_wait: "Дождитесь, пока стихнет шум за окном",
    retry_again: "Прочитать снова",

    label_heard: "Что мы услышали",
    label_fix: "Как исправить",
    label_drill: "Упражнение",
    teacher_note: "Мы не вполне уверены — проверьте с вашим устозом.",
    wrong_button: "Оценка неверна",
    wrong_thanks: "Спасибо. Мы это разберём.",

    draft_chip: "ЧЕРНОВИК",
    draft_note: "Это замечание не проверено чтецом. Только для тестирования.",
    draft_unauthored: "Для этой ошибки текст вообще не написан. Только код:",
    draft_banner_title: "Показываются непроверенные замечания",
    draft_banner_body:
      "Включён TILAWAH_SHOW_UNREVIEWED: показываются все найденные ошибки, включая непроверенные чтецом. Это режим разработчика.",

    pick_sura: "Выберите суру",
    search_sura: "Название или номер суры",
    no_matches: "Ничего не найдено.",
    pick_ayah: "Выберите аят.",
    pick_segment: "Какую часть будете читать?",
    ayat_count: "аятов",
    parts: "частей",
    words: "слова",
    seconds_short: "с",
    estimate: "Примерная длительность",
    change_selection: "Выбрать другой аят",

    library_title: "Аяты",
    library_sub: "Выберите аят для практики.",
    level: "Уровень",

    log_title: "Записи",
    log_sub: "Ваши последние чтения.",
    log_empty: "Пока нет записанных чтений.",
    log_clear: "Без ошибок",
    log_noted: "Есть замечание",
    log_retry: "Перезаписано",

    pilot_title: "Пробная версия",
    pilot_body:
      "Приложение ещё тестируется. Замечания по таджвиду пока не полностью выверены — сверяйтесь с вашим устозом.",

    consent_title: "Ваши данные",
    consent_body:
      "Если разрешите сохранять чтения, вы увидите историю, а мы улучшим качество оценки. Удалить можно в любой момент.",
    consent_toggle: "Разрешаю сохранять мои чтения",
    consent_delete: "Все ваши данные удалены.",

    consent_gate_title: "Ваши данные принадлежат вам",
    consent_gate_intro:
      "Прежде чем начать, договоримся: вы решаете, что сохранять. По умолчанию не сохраняется ничего.",
    consent_gate_none_title: "Ничего не сохраняется",
    consent_gate_none_body:
      "Без разрешения чтение будет оценено и сразу забыто. Приложением можно пользоваться полностью.",
    consent_attempts_label: "Сохранять историю моих чтений",
    consent_attempts_help:
      "Сохраняется, какой аят вы читали и какое замечание получили. Голос не сохраняется.",
    consent_audio_label: "Сохранять мои голосовые записи",
    consent_audio_help:
      "Голос сохраняется и используется только для улучшения качества оценки. Это отдельное разрешение — не отмечайте, если не хотите.",
    consent_gate_accept: "Продолжить",
    consent_gate_skip: "Продолжить, ничего не сохраняя",
    consent_gate_footer:
      "Решение можно изменить в разделе «Записи» в любой момент. При отзыве всё сохранённое действительно удаляется.",

    error_generic: "Произошла ошибка. Попробуйте ещё раз.",
    loading: "Загрузка",
  },
} as const;

export type Key = keyof (typeof STRINGS)["uz"];

export function t(lang: Lang, key: Key): string {
  return STRINGS[lang][key];
}

export function retryCopy(lang: Lang, reason: string) {
  if (reason === "too_short")
    return {
      title: t(lang, "retry_short_title"),
      body: t(lang, "retry_short_body"),
      tips: [] as string[],
    };
  if (reason === "too_long")
    return {
      title: t(lang, "retry_long_title"),
      body: t(lang, "retry_long_body"),
      tips: [] as string[],
    };
  if (reason === "too_quiet")
    return {
      title: t(lang, "retry_quiet_title"),
      body: t(lang, "retry_quiet_body"),
      tips: [t(lang, "retry_tip_close")],
    };
  // The model returned huruf muqatta'at — it could not resolve the recitation.
  // Usually a truncated take, so lead with reciting the ayah in full.
  if (reason === "unclear_recitation")
    return {
      title: t(lang, "retry_unclear_title"),
      body: t(lang, "retry_unclear_body"),
      tips: [
        t(lang, "retry_tip_full"),
        t(lang, "retry_tip_pause"),
        t(lang, "retry_tip_room"),
      ],
    };
  return {
    title: t(lang, "retry_noisy_title"),
    body: t(lang, "retry_noisy_body"),
    tips: [
      t(lang, "retry_tip_room"),
      t(lang, "retry_tip_close"),
      t(lang, "retry_tip_wait"),
    ],
  };
}
