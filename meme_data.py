#!/usr/bin/env python3
"""
Данные для мемов и их рейтингов
"""
import logging
from content_filter import is_suitable_meme

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Источники мемов для офисных работников и не только
MEME_SOURCES = [
    "https://vk.com/public212383311", # Мемы для офисных работников
    "https://vk.com/office_rat",       # Офисная крыса мемы
    "https://vk.com/corporateethics", # Корпоративная этика
    "https://vk.com/club211736252",   # Нетворкинг мемы
    "https://vk.com/hr_mem",          # HR мемы
    "https://vk.com/workbench_mem",   # Рабочие мемы
    "https://vk.com/the_working_day", # Типичный рабочий день
    "https://vk.com/office.mems",     # Офисные мемы для менеджеров
    "https://vk.com/zapiskibezdushi", # Записки офисного работника 
    "https://vk.com/office_plankton", # Офисный планктон
]

# Коллекция мемов
# Ключ - уникальный ID мема
# Значение - словарь с информацией о меме
MEMES = {
    "1": {
        "text": "Когда выполнил план продаж и можешь отдохнуть несколько минут",
        "image_url": "https://sun9-3.userapi.com/impg/4yxA9T8JyU8Fv-vn5Cna1HpUizMZxqWkw9r5sA/qyXs0jy6vQY.jpg?size=1280x1280&quality=95&sign=cf56a7257e4ec7fb5e7d38c48c3d9909&type=album",
        "source": "office_plankton",
        "tags": ["офис", "усталость", "план продаж"]
    },
    "2": {
        "text": "Я в конце рабочего дня",
        "image_url": "https://sun9-76.userapi.com/impg/UJrx-P9l54LMO8C-Njo0UB1f9RnvCrlrYKMi3g/wWXMhcKTLn0.jpg?size=720x692&quality=95&sign=03aa1e196b6ce7acd17a3a5cf95a2dc2&type=album",
        "source": "office_rat",
        "tags": ["офис", "усталость", "конец дня"]
    },
    "3": {
        "text": "Когда работаешь с опытным коллегой и пока не понимаешь, что происходит",
        "image_url": "https://sun9-66.userapi.com/impg/9Q45_Yd6-lkZwLB5rVHbxLELbHyAjT1vHZQMoA/9rCY94ZHPbw.jpg?size=1080x1080&quality=95&sign=3c23c1b9f2ac8c18f4f15ae41e9f7f7c&type=album",
        "source": "corporateethics",
        "tags": ["офис", "обучение", "новичок"]
    },
    "4": {
        "text": "Начальник: \"У тебя все готово?\" Я, который ничего не сделал:",
        "image_url": "https://sun9-75.userapi.com/impg/fmFZQmjj6dS1mwwcxTrObvUFJDlCE2qIXjxhWA/jMoVSPV2ZyY.jpg?size=640x640&quality=95&sign=fee9ccec851aafc3d4ad6e1704cd6ddb&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "дедлайн", "начальник"]
    },
    "5": {
        "text": "Коллега за две минуты до окончания рабочего дня:",
        "image_url": "https://sun9-48.userapi.com/impg/5lPDzGWDqQzpd2Nxu3gE9-fWu0OMZWDpIe5SQQ/C-hcHXQmQG0.jpg?size=500x500&quality=95&sign=b8afb7e5e34a47a16aea1dee2995b7f3&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "конец дня", "коллеги"]
    },
    "6": {
        "text": "Когда пытаешься объяснить боссу, что тебе нужно больше времени для выполнения задачи",
        "image_url": "https://sun9-16.userapi.com/impg/xlfxQQIu90lLU3QNhgP9-4YrNZlmQGtMzxqRXw/N__2Qs0IuHM.jpg?size=720x540&quality=95&sign=9f8dbb08d9f52bb72c94b4848b1116fa&type=album",
        "source": "office_mems",
        "tags": ["офис", "дедлайн", "начальник"]
    },
    "7": {
        "text": "Я после весёлых выходных в понедельник на работе",
        "image_url": "https://sun9-6.userapi.com/impg/Mm3K9N2p2ib-5xV5fmxvw_VxLHxTwcFIPVmrEg/2nnEKCHmBiM.jpg?size=1080x1350&quality=95&sign=ff9a20c4e9d6c8f2bbe30bc0e0dbea66&type=album",
        "source": "the_working_day",
        "tags": ["офис", "понедельник", "выходные"]
    },
    "8": {
        "text": "Когда вместо отпуска получил еще один проект",
        "image_url": "https://sun9-44.userapi.com/impg/lsrPM9UHGcPdudEEXlnr7JXqpx8lhprjuAOylw/wOAPD65Ue3Y.jpg?size=1080x1080&quality=95&sign=2ead1cef8b48fb4bc9c4ff6d68f5747a&type=album",
        "source": "hr_mem",
        "tags": ["офис", "отпуск", "проект"]
    },
    "9": {
        "text": "HR-менеджер: у нас дружный коллектив и комфортная атмосфера. Коллектив и атмосфера:",
        "image_url": "https://sun9-68.userapi.com/impg/6kRMWPvgB_zLvBXCEcOVV2-yVj_w9hNLSGp5hQ/wVKyR6vPTwI.jpg?size=474x442&quality=95&sign=a6a6f93cf99cf95dc71b17b8aa7f47fa&type=album",
        "source": "hr_mem",
        "tags": ["офис", "HR", "собеседование"]
    },
    "10": {
        "text": "Отдел маркетинга: придумал идею! Отдел разработки, который должен это реализовать:",
        "image_url": "https://sun9-58.userapi.com/impg/wCLcXYJ-Fxl2HI0C5IA6DTNOFaUQlzQAi-IXcw/N3DGP5dHUdQ.jpg?size=720x651&quality=95&sign=d3a5b61dd1fdc03cba85b9953aff5a4c&type=album",
        "source": "office_rat",
        "tags": ["офис", "маркетинг", "разработка"]
    },
    "11": {
        "text": "Я и мои коллеги, понимая, что до конца рабочего дня осталось 30 минут",
        "image_url": "https://sun9-69.userapi.com/impg/AuHAXL88Qu1aGgLAPytOXL-R3PZnHcQ15PBlFg/u3_HRW_Vg5I.jpg?size=1072x1080&quality=95&sign=a1fd8aa1c8a54b3c1b9f08fc6e3e8d61&type=album",
        "source": "the_working_day",
        "tags": ["офис", "конец дня", "коллеги"]
    },
    "12": {
        "text": "Начальник: \"Нужно срочно выполнить эту задачу!\". Мои нейроны, пытающиеся понять, с чего начать:",
        "image_url": "https://sun9-53.userapi.com/impg/pALkrDKMt3Dp0xTfuuIQFrR1bYI3uXyKyvyBHQ/WXuNm_zCjZs.jpg?size=460x460&quality=95&sign=3bbe3de913db56f8f38c89c7f00cbb1b&type=album",
        "source": "corporateethics",
        "tags": ["офис", "задачи", "начальник"]
    },
    "13": {
        "text": "Как я представляю работу из дома vs Как я работаю из дома на самом деле",
        "image_url": "https://sun9-5.userapi.com/impg/vBPzP-pE6mT_RKNBWPi3GMTzHxl3eU-M2U90DQ/HsFGHFHZJZ8.jpg?size=960x720&quality=95&sign=9c4479a9ebb0ece4dbf4ca5b5edaeea3&type=album",
        "source": "office_plankton",
        "tags": ["удаленка", "работа из дома", "офис"]
    },
    "14": {
        "text": "Когда пришел на работу с температурой 38, но тебе очень нужны эти деньги",
        "image_url": "https://sun9-28.userapi.com/impg/HmfBpHjwTg5bQYBSoG8HYtTIFLBuQvpLZc9YGA/KJDPpQwRUG0.jpg?size=1080x1080&quality=95&sign=651a99d7be4cc8c8e91be32b4ee4f7f8&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "болезнь", "работа"]
    },
    "15": {
        "text": "Как думают мои родители, что я работаю vs Как я работаю на самом деле",
        "image_url": "https://sun9-3.userapi.com/impg/7rxkE4v7Y1-Ga0MRY9A46_a7WCEgAGYXrLsz0w/7Jl3zL1AVDM.jpg?size=1080x1080&quality=95&sign=aed6b3fcf8893edf3aa1d79e8c7bac7e&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "родители", "реальность"]
    },
    "16": {
        "text": "Когда задачу нужно было сделать вчера, а тебе только что о ней сказали",
        "image_url": "https://sun9-32.userapi.com/impg/YF4vJ26Eg9hkf9CKxqcYCvO7yqb8WNMO7MCGIw/QDlXWdNr-ZA.jpg?size=1080x1080&quality=95&sign=3d4cd85d8b36a39ecc5ec49005e78b6f&type=album",
        "source": "office_mems",
        "tags": ["офис", "дедлайн", "задачи"]
    },
    "17": {
        "text": "Моя продуктивность в течение рабочего дня",
        "image_url": "https://sun9-54.userapi.com/impg/qxVvfQQbGT32pDpQHX89VXBJ7UHQCrVtpUO16w/_oEjgYdTD0c.jpg?size=640x640&quality=95&sign=6ebe1e3df4cc9ff4a36b65ab9cde0c02&type=album",
        "source": "office_plankton",
        "tags": ["офис", "продуктивность", "график"]
    },
    "18": {
        "text": "Менеджер проектов в пятницу вечером: «А давайте соберемся в понедельник в 8 утра и все обсудим»",
        "image_url": "https://sun9-71.userapi.com/impg/9-TBtIIb-AxU6pGNuSYMvETZLMy9Nf0OEjO96A/xSr0bYJM2h0.jpg?size=1280x720&quality=95&sign=d91f4aecf8b1c09e36c4cc39db1a8d90&type=album",
        "source": "corporateethics",
        "tags": ["офис", "менеджер", "встречи"]
    },
    "19": {
        "text": "Я: хочу взять отпуск в следующем месяце. Начальник:",
        "image_url": "https://sun9-61.userapi.com/impg/n46Rlr7XlQORNULIEPH_W1OoR0xhDRNPVxPzwA/6qMsw_Pj_yw.jpg?size=720x597&quality=95&sign=e9a9ce0c01e7a7b842e1e29363e19c1b&type=album",
        "source": "hr_mem",
        "tags": ["офис", "отпуск", "начальник"]
    },
    "20": {
        "text": "Когда отправил письмо с ошибками и только потом это заметил",
        "image_url": "https://sun9-45.userapi.com/impg/JlI-oMGBQ1eB_s99OJnC1QznPtDt6DyxDI2JlA/rZ_LRw1Wpho.jpg?size=1080x1031&quality=95&sign=0b7ba2d0b05ca968ff77cb7ca9d2b7a4&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "письмо", "ошибка"]
    },
    "21": {
        "text": "Первый день на новой работе. Я и мои новые коллеги:",
        "image_url": "https://sun9-29.userapi.com/impg/_rMDqhyvT7Nc2K7_OQO7n3CYw1R9YbMvMDPcMw/1wkRNmPM2Kk.jpg?size=750x795&quality=95&sign=9ca78b9e4e5fd82b2b9ffe44e7ddf7fa&type=album",
        "source": "office_rat",
        "tags": ["офис", "новая работа", "знакомство"]
    },
    "22": {
        "text": "Когда пришло время ежегодного корпоратива, а ты интроверт",
        "image_url": "https://sun9-45.userapi.com/impg/OxRH70WEkD9G0J06c9j4Ox4nFAF-p8RGxzjb-A/BIx59S0SnGk.jpg?size=807x508&quality=95&sign=e3e5f26d9a3908a34f8a2f8a27aa3e5e&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "корпоратив", "интроверт"]
    },
    "23": {
        "text": "Я на совещании, когда никто не знает ответ, а взгляд начальника падает на меня",
        "image_url": "https://sun9-67.userapi.com/impg/2UwwEBktXBMT30a9Y72KVyKD0K9iEp49D8eSDA/dVBvgIvPFEk.jpg?size=750x734&quality=95&sign=c6246ec2b10e77c15eb82b6bc4c4de37&type=album",
        "source": "the_working_day",
        "tags": ["офис", "совещание", "начальник"]
    },
    "24": {
        "text": "Я после того, как ответил на рабочую почту в нерабочее время",
        "image_url": "https://sun9-30.userapi.com/impg/2qrDp1Nrjhl27gJ8uyN7RRUJjfZdm1fMGhj1iw/Ol2UVwgDZEM.jpg?size=720x708&quality=95&sign=fc0c232a1aa2a8c9c2f68b72f6708e45&type=album",
        "source": "corporateethics",
        "tags": ["офис", "почта", "нерабочее время"]
    },
    "25": {
        "text": "Когда с утра уже третья внеплановая встреча",
        "image_url": "https://sun9-43.userapi.com/impg/fTqbDBZkY55ixj3WdnQXibgxTPsOXVYozT_QPQ/UqQP9rUF1UU.jpg?size=736x736&quality=95&sign=4343ba8ee35f5cffd44064d9f56e1eb3&type=album",
        "source": "office_mems",
        "tags": ["офис", "встреча", "совещание"]
    },
    "26": {
        "text": "Моя мотивация в начале месяца vs. Моя мотивация в конце месяца",
        "image_url": "https://sun9-68.userapi.com/impg/jqzPK4iELLpcGcFiBb22bsaIFFmUXHcnw2EcuQ/I_R1c2r_9TI.jpg?size=1080x1080&quality=95&sign=dc08c2c47ca3c2a14ca1cef7a95a14fc&type=album",
        "source": "office_plankton",
        "tags": ["офис", "мотивация", "месяц"]
    },
    "27": {
        "text": "Что у меня на рабочем столе компьютера vs что видит начальник",
        "image_url": "https://sun9-61.userapi.com/impg/FrHOYdBH3Kh6xVmFXLZxOIQZOZtvQCPYZ9vKDw/lqvUa12JxPE.jpg?size=1080x1080&quality=95&sign=44c5cd36b1a183bacdcb5c2f05f47a74&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "компьютер", "начальник"]
    },
    "28": {
        "text": "На собеседовании: «Опишите себя тремя словами». Я: «Плохо считаю»",
        "image_url": "https://sun9-79.userapi.com/impg/hfRjpKlFVvyFExGqkhHh_0GKf73u3aQhQ1qofw/1tqgIpvLLnQ.jpg?size=700x700&quality=95&sign=7cffc86ac15d3d3053cbff9fdcb5fca6&type=album",
        "source": "hr_mem",
        "tags": ["офис", "собеседование", "юмор"]
    },
    "29": {
        "text": "Системный администратор: «Вы пробовали перезагрузить компьютер?» Я с десятком незакрытых программ:",
        "image_url": "https://sun9-31.userapi.com/impg/TmEjZh_YQmCYBXXvzqRKqGAjFsLWLNnNtZL3nw/hjyqYppDXOU.jpg?size=460x650&quality=95&sign=ffd6e9b4d654d5ecedb2bd8a93e81fb8&type=album",
        "source": "the_working_day",
        "tags": ["офис", "IT", "компьютер"]
    },
    "30": {
        "text": "Я и мои коллеги, пытающиеся разобраться в техническом задании от заказчика",
        "image_url": "https://sun9-58.userapi.com/impg/HgnzOLg9QfYYWKfUCy2KG-_D6xM4yQIoNnhI1A/bDO44o_K5LE.jpg?size=1080x1080&quality=95&sign=7c19d39af1e2c2bc77b0edb59b2a7dd3&type=album",
        "source": "corporateethics",
        "tags": ["офис", "ТЗ", "заказчик"]
    },
    "31": {
        "text": "Когда после собеседования начинаешь гуглить, что они имели в виду под 'динамичной и быстроразвивающейся компанией'",
        "image_url": "https://sun9-72.userapi.com/impg/c857624/v857624215/17fef8/5KlUWxI9-qM.jpg?size=807x594&quality=96&sign=81f26344bd5e0af4e4eb586a338e7b21&type=album",
        "source": "office_plankton",
        "tags": ["офис", "собеседование", "работа"]
    },
    "32": {
        "text": "Когда видишь своего коллегу в нерабочее время и вам обоим неловко",
        "image_url": "https://sun9-9.userapi.com/impg/c855536/v855536002/1d4e17/H6oP0T6J9xc.jpg?size=504x560&quality=96&sign=da9a0ebd2c3bb22202c068c54a4cf43f&type=album",
        "source": "corporateethics",
        "tags": ["офис", "коллеги", "неловкость"]
    },
    "33": {
        "text": "Когда босс говорит «у нас не офис, а семья», но продолжает увольнять людей",
        "image_url": "https://sun9-81.userapi.com/impg/c853428/v853428007/1b6abb/FmI7fty8AKk.jpg?size=600x436&quality=96&sign=08c3437a2b5968ab24b4aef60c6df0e2&type=album",
        "source": "office_rat",
        "tags": ["офис", "босс", "увольнение"]
    },
    "34": {
        "text": "Мои коллеги: рассказывают о своих детях, ипотеке и планах на будущее. Я:",
        "image_url": "https://sun9-78.userapi.com/impg/c855228/v855228887/204fa7/MzJTtTaFD5c.jpg?size=480x480&quality=96&sign=8bad51d0ce5bb9ccb9d05df1f8c0f1b2&type=album",
        "source": "the_working_day",
        "tags": ["офис", "коллеги", "разговоры"]
    },
    "35": {
        "text": "Удалёнка, день пятый: не вижу смысла надевать штаны на онлайн-совещание",
        "image_url": "https://sun9-26.userapi.com/impg/c857632/v857632939/133cf4/1EeO2vqZfaU.jpg?size=640x640&quality=96&sign=7ac3ec9f61ff3ce98f13e75ed8a6a6f9&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "удаленка", "совещание"]
    },
    "36": {
        "text": "Когда тебя просят обучить нового сотрудника, но ты сам еще ничего не знаешь",
        "image_url": "https://sun9-57.userapi.com/impg/c855020/v855020905/23e32d/o48PEtUaUc0.jpg?size=1280x960&quality=96&sign=e18a2fc1b6093c7fcc40f6f88d33a8a3&type=album",
        "source": "hr_mem",
        "tags": ["офис", "обучение", "новичок"]
    },
    "37": {
        "text": "Работа в офисе vs Работа из дома: ожидание vs реальность",
        "image_url": "https://sun9-6.userapi.com/impg/c858032/v858032824/1c4df2/z_B5eSzqWRE.jpg?size=1080x1080&quality=96&sign=cf72340c1e2be67d7fbca736c9598e78&type=album",
        "source": "office_plankton",
        "tags": ["офис", "удаленка", "работа из дома"]
    },
    "38": {
        "text": "Когда объясняешь начальнику, что задача занимает больше времени, чем он думает",
        "image_url": "https://sun9-57.userapi.com/impg/c858320/v858320824/bc11c/hYUhBIxS2_U.jpg?size=1280x853&quality=96&sign=56afa05e75c7d5a5a82608e6c12c0514&type=album",
        "source": "office_mems",
        "tags": ["офис", "начальник", "задачи"]
    },
    "39": {
        "text": "В резюме: стрессоустойчивость. Я, когда принтер не печатает:",
        "image_url": "https://sun9-17.userapi.com/impg/c858336/v858336532/181c8/R93FHhKIrFE.jpg?size=736x736&quality=96&sign=81e8b18d0d6c73d9a22c88fce3a0fd5e&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "принтер", "стресс"]
    },
    "40": {
        "text": "На собеседовании: «Расскажите о себе». Я: «Мне нужны деньги»",
        "image_url": "https://sun9-40.userapi.com/impg/c857320/v857320654/1a72c6/Ek3vAcZfwFM.jpg?size=680x680&quality=96&sign=e77dd69e78f5c3db70aa52b33b0bf9a0&type=album",
        "source": "hr_mem",
        "tags": ["офис", "собеседование", "деньги"]
    },
    "41": {
        "text": "Когда все кричат на совещании, а ты вообще не понимаешь, о чем речь",
        "image_url": "https://sun9-79.userapi.com/impg/T7v5Rh5rE57rNpVa5hwXbpPyDlLiuH8MuUFCGQ/WmmbkxDSgd8.jpg?size=640x640&quality=96&sign=17eeea0baed0a8a20fac3a978fc7ef80&type=album",
        "source": "the_working_day",
        "tags": ["офис", "совещание", "непонимание"]
    },
    "42": {
        "text": "Когда отправил резюме на 50 вакансий и ни одного ответа",
        "image_url": "https://sun9-53.userapi.com/impg/c855132/v855132349/e3c17/qY-AfmrSwkE.jpg?size=600x586&quality=96&sign=94a0e4a6f5ae6dbc9a9abe51fd7b3023&type=album",
        "source": "hr_mem",
        "tags": ["офис", "резюме", "поиск работы"]
    },
    "43": {
        "text": "Когда совещание можно было провести в формате электронного письма",
        "image_url": "https://sun9-28.userapi.com/impg/c855124/v855124461/215ea8/5Td0eZHTOdQ.jpg?size=750x562&quality=96&sign=3faa2dd06aa2fc2e3c1a15e68c6a46f9&type=album",
        "source": "office_mems",
        "tags": ["офис", "совещание", "время"]
    },
    "44": {
        "text": "Когда босс заставляет работать в выходные, но платит за сверхурочные",
        "image_url": "https://sun9-31.userapi.com/impg/c857720/v857720788/5d349/E74RWMLuvt0.jpg?size=640x427&quality=96&sign=91ba1d03ebacdb59c3f05ee1ca08d96d&type=album",
        "source": "office_plankton",
        "tags": ["офис", "выходные", "сверхурочные"]
    },
    "45": {
        "text": "Когда через 10 минут после начала рабочего дня уже хочешь домой",
        "image_url": "https://sun9-34.userapi.com/impg/c854124/v854124069/6b1c2/lHTkQT8X1FE.jpg?size=500x333&quality=96&sign=90f7eab2b3747f5183be36ee9ffbee63&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "рабочий день", "усталость"]
    },
    "46": {
        "text": "Когда начальник сказал, что можно уйти пораньше",
        "image_url": "https://sun9-12.userapi.com/impg/c855216/v855216069/187e8b/HhWAc_xSrkE.jpg?size=720x720&quality=96&sign=b4f61acf84c63f78c63e7cfcbd1bd61f&type=album",
        "source": "the_working_day",
        "tags": ["офис", "конец дня", "радость"]
    },
    "47": {
        "text": "Когда приходишь на работу с похмелья, а там совещание",
        "image_url": "https://sun9-27.userapi.com/impg/c854228/v854228621/52abb/-bONhDwIuLA.jpg?size=493x700&quality=96&sign=bceacc2fba2560b63e0a1ba8b059e2b1&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "похмелье", "совещание"]
    },
    "48": {
        "text": "Весь офис, когда IT-специалист пытается починить принтер",
        "image_url": "https://sun9-79.userapi.com/impg/c858236/v858236114/bac0c/WbAXLiTNH_c.jpg?size=600x600&quality=96&sign=6b2a13b1a93a26bc0b2b1feaa3caf1e5&type=album",
        "source": "office_rat",
        "tags": ["офис", "IT", "принтер"]
    },
    "49": {
        "text": "Когда ты что-то объясняешь коллеге, а он делает всё по-своему",
        "image_url": "https://sun9-41.userapi.com/impg/c858024/v858024459/2a75d/Nma-l06Cxo0.jpg?size=720x709&quality=96&sign=0a77053a9d8c46f8a93c4b1d6a3a33c9&type=album",
        "source": "corporateethics",
        "tags": ["офис", "коллеги", "объяснение"]
    },
    "50": {
        "text": "Когда переделываешь всю работу за час до дедлайна",
        "image_url": "https://sun9-27.userapi.com/impg/c857736/v857736399/ec87c/b04eTnGIZUA.jpg?size=640x640&quality=96&sign=d7a99d17ba37e5bf0e43d9a994d47ffa&type=album",
        "source": "office_plankton",
        "tags": ["офис", "дедлайн", "работа"]
    },
    "51": {
        "text": "Когда говоришь клиенту, что отправил ему e-mail, а сам только начинаешь его писать",
        "image_url": "https://sun9-83.userapi.com/impg/c857432/v857432326/de633/vw6LFy2QpSU.jpg?size=750x742&quality=96&sign=c78a9a29c5d3a5fe473a9b6834fd9c44&type=album",
        "source": "office_mems",
        "tags": ["офис", "клиент", "e-mail"]
    },
    "52": {
        "text": "Когда нужно делать презентацию, а ты не знаешь, о чем она",
        "image_url": "https://sun9-37.userapi.com/impg/c857336/v857336645/a0b7c/nRrOmJ2N3rk.jpg?size=640x601&quality=96&sign=7c54c0cb8ce4c26db4c2e3b87d5fd37e&type=album",
        "source": "the_working_day",
        "tags": ["офис", "презентация", "паника"]
    },
    "53": {
        "text": "Когда все принесли обед из дома, а ты забыл",
        "image_url": "https://sun9-50.userapi.com/impg/c857132/v857132361/f92cf/e2wCWoUGDEI.jpg?size=586x604&quality=96&sign=6e2b75b3e7b59b6fc3b25ee52d9cc9c3&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "обед", "забывчивость"]
    },
    "54": {
        "text": "Когда приходишь в офис и понимаешь, что забыл ID-карту дома",
        "image_url": "https://sun9-29.userapi.com/impg/c857520/v857520282/102b84/ZDFuHJFWE08.jpg?size=500x500&quality=96&sign=f9c8ad4cd40cb03a48cc0e4d4dfa4b5a&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "ID-карта", "вход"]
    },
    "55": {
        "text": "HR на собеседовании: «У нас дружный коллектив!» Коллектив:",
        "image_url": "https://sun9-25.userapi.com/impg/c855436/v855436740/1d78e5/JZq8YC_NpHA.jpg?size=900x602&quality=96&sign=95fa2c72b8efa921c02d00d2ee54e4ae&type=album",
        "source": "hr_mem",
        "tags": ["офис", "коллектив", "HR"]
    },
    "56": {
        "text": "Когда увидел зарплату в другой компании на той же должности",
        "image_url": "https://sun9-78.userapi.com/impg/c858332/v858332759/8d92b/ycTjTnJ_8rc.jpg?size=750x747&quality=96&sign=d0c3f01c14f6f33ebbc07b78d252c57d&type=album",
        "source": "office_rat",
        "tags": ["офис", "зарплата", "сравнение"]
    },
    "57": {
        "text": "Я и мои коллеги, когда директор ушел на совещание",
        "image_url": "https://sun9-10.userapi.com/impg/c853520/v853520666/1c12e1/vn1nVvyY85k.jpg?size=575x604&quality=96&sign=ebffc2b21f73ce58b80a4e6c81ba6c67&type=album",
        "source": "corporateethics",
        "tags": ["офис", "директор", "свобода"]
    },
    "58": {
        "text": "Когда на совещании говорят, что проект нужно сделать без бюджета, но с блэкджеком",
        "image_url": "https://sun9-76.userapi.com/impg/c855024/v855024922/1e5cc5/eaAm3bV-xQ4.jpg?size=720x404&quality=96&sign=44d0fe65eb507a7ffe5cb33b5ab76a19&type=album",
        "source": "office_plankton",
        "tags": ["офис", "проект", "бюджет"]
    },
    "59": {
        "text": "Когда работаешь 12 часов подряд, а работы только прибавляется",
        "image_url": "https://sun9-58.userapi.com/impg/c855224/v855224069/1d6e71/n7xd4qGYU4g.jpg?size=600x314&quality=96&sign=96adbaa2c8e9f83f5a4dbc20d8c9f8e2&type=album",
        "source": "office_mems",
        "tags": ["офис", "перегруз", "работа"]
    },
    "60": {
        "text": "Описание вакансии: «Требуется сотрудник с опытом работы 5 лет и зарплатой как у стажера»",
        "image_url": "https://sun9-35.userapi.com/impg/c855128/v855128207/1f2f0b/v0eAzXB2YDA.jpg?size=1080x1223&quality=96&sign=835fb7f8d881ab72f99878e3ee3a2613&type=album",
        "source": "hr_mem",
        "tags": ["офис", "вакансия", "зарплата"]
    },
    "61": {
        "text": "Моя продуктивность в понедельник против пятницы",
        "image_url": "https://sun9-2.userapi.com/impg/c855424/v855424943/177e6f/OxoJxd7EWX8.jpg?size=1125x793&quality=96&sign=99b96752dc7a94e7c6d3cfe7a87cb8ef&type=album",
        "source": "the_working_day",
        "tags": ["офис", "продуктивность", "неделя"]
    },
    "62": {
        "text": "Когда узнал, что твой коллега получает больше за ту же работу",
        "image_url": "https://sun9-71.userapi.com/impg/c857416/v857416521/108bfe/3yBn30XO_Bw.jpg?size=675x675&quality=96&sign=723bef0c775c4cf2da2a4db8b4deefa4&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "зарплата", "несправедливость"]
    },
    "63": {
        "text": "Когда отправил важное сообщение не тому коллеге",
        "image_url": "https://sun9-63.userapi.com/impg/c857616/v857616521/eae37/rK7QJxoDlNU.jpg?size=640x640&quality=96&sign=b83a1af1eac4f6c1bf7498d95e347cbc&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "сообщение", "ошибка"]
    },
    "64": {
        "text": "Когда начальник спрашивает, почему я опоздал, а я придумываю на ходу",
        "image_url": "https://sun9-71.userapi.com/impg/c855220/v855220521/b4cef/vSM9YpRfPzk.jpg?size=640x551&quality=96&sign=bfd1bdb50c1a22ace85f1780eb6089fe&type=album",
        "source": "office_rat",
        "tags": ["офис", "опоздание", "начальник"]
    },
    "65": {
        "text": "Когда отдел закупок выбрал самого дешевого подрядчика",
        "image_url": "https://sun9-53.userapi.com/impg/c855036/v855036075/21efbf/lvdgjSVffDk.jpg?size=640x640&quality=96&sign=37c18df09d1b47d15ece6ff6b09cf9b5&type=album",
        "source": "corporateethics",
        "tags": ["офис", "закупки", "экономия"]
    },
    "66": {
        "text": "Я, когда HR звонит с результатами собеседования",
        "image_url": "https://sun9-23.userapi.com/impg/c858036/v858036026/119a36/wVhf6SgMPNQ.jpg?size=473x512&quality=96&sign=d94ac83c30fc5b7f0be40a76cef95c02&type=album",
        "source": "hr_mem",
        "tags": ["офис", "собеседование", "звонок"]
    },
    "67": {
        "text": "Когда коллега в копировальном центре не может разобраться с очередным замятием бумаги",
        "image_url": "https://sun9-56.userapi.com/impg/c857336/v857336264/c24fe/Kbgv_JMHlq0.jpg?size=720x723&quality=96&sign=8f3fc29e87a03d0ea1ed1b58e63c6f5f&type=album",
        "source": "office_plankton",
        "tags": ["офис", "принтер", "бумага"]
    },
    "68": {
        "text": "Когда только устроился на работу и хочешь произвести хорошее впечатление",
        "image_url": "https://sun9-83.userapi.com/impg/c855328/v855328944/19ca88/PZmAPhjtcjs.jpg?size=564x564&quality=96&sign=cca8e0c602d2a7d88c35f4b2fceb9f45&type=album",
        "source": "the_working_day",
        "tags": ["офис", "первый день", "впечатление"]
    },
    "69": {
        "text": "Когда офисная кухня на 25 человек, но все приходят на обед одновременно",
        "image_url": "https://sun9-24.userapi.com/impg/c855232/v855232889/1a8f6f/S3z59BVp2uE.jpg?size=700x700&quality=96&sign=8d1f5ec5ab1e8c91ca1d1d4f6d66cee7&type=album",
        "source": "office_mems",
        "tags": ["офис", "кухня", "обед"]
    },
    "70": {
        "text": "Когда написал важное письмо и переживаешь, что там ошибка",
        "image_url": "https://sun9-31.userapi.com/impg/c857336/v857336607/a34fc/bJ4Uo4gUvj0.jpg?size=720x713&quality=96&sign=db14f87e98f9dd15f1d66c3ab77e28c2&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "письмо", "ошибка"]
    },
    "71": {
        "text": "Когда на корпоративе выпил лишнего и танцевал со всеми, а теперь нужно смотреть в глаза коллегам",
        "image_url": "https://sun9-63.userapi.com/impg/c855216/v855216069/1a3bc/hHOPJgabVFU.jpg?size=1280x720&quality=96&sign=2c8175d4d97953c8a2c4a8fdba6fb7a8&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "корпоратив", "стыд"]
    },
    "72": {
        "text": "Когда в офисе отключили интернет, а работать как-то надо",
        "image_url": "https://sun9-74.userapi.com/impg/c857136/v857136070/cad3d/8aFH6FWxLFk.jpg?size=807x538&quality=96&sign=14e642b9e12ef17c28257c6c7de59cf9&type=album",
        "source": "office_rat",
        "tags": ["офис", "интернет", "работа"]
    },
    "73": {
        "text": "Когда пытаешься объяснить боссу, что его идея нереализуема",
        "image_url": "https://sun9-54.userapi.com/impg/c857128/v857128267/10eec3/bZhQENYM-Fw.jpg?size=1080x1080&quality=96&sign=52ef902c38f40d4f51a6c4bbeaf90afc&type=album",
        "source": "corporateethics",
        "tags": ["офис", "босс", "идеи"]
    },
    "74": {
        "text": "Счастье, когда в офисе есть кофемашина",
        "image_url": "https://sun9-1.userapi.com/impg/c858132/v858132997/99b89/H9-HwsWxX9c.jpg?size=552x534&quality=96&sign=bc1c68dd8d7dbd0e5bc7580bc6a18e2a&type=album",
        "source": "office_plankton",
        "tags": ["офис", "кофе", "кофемашина"]
    },
    "75": {
        "text": "Когда ты думал, что совещание закончится через час, а оно затянулось на весь день",
        "image_url": "https://sun9-8.userapi.com/impg/c856036/v856036070/194bd2/q9lK1t9A5Nw.jpg?size=600x335&quality=96&sign=8c72e58adf2ad77d9b0c24cc70af4c0a&type=album",
        "source": "the_working_day",
        "tags": ["офис", "совещание", "длительность"]
    },
    "76": {
        "text": "Когда начальник говорит, что сегодня можно уйти пораньше, но без зарплаты",
        "image_url": "https://sun9-20.userapi.com/impg/c858320/v858320824/121a22/uPZnSOmPTzY.jpg?size=700x525&quality=96&sign=8db0d8b61b67c0433664d172a6fa4b36&type=album",
        "source": "office_mems",
        "tags": ["офис", "начальник", "зарплата"]
    },
    "77": {
        "text": "Когда все выходят курить, а ты не куришь",
        "image_url": "https://sun9-27.userapi.com/impg/c856136/v856136033/17c9c7/Zcz6Q2GF-zU.jpg?size=720x741&quality=96&sign=9cc04d8a99e72be0f3953a8bdfbab70e&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "курение", "перерыв"]
    },
    "78": {
        "text": "Когда прогуливаешь работу, а потом видишь коллегу в магазине",
        "image_url": "https://sun9-58.userapi.com/impg/c854328/v854328943/1ece0/c-vIwpdbGZY.jpg?size=720x631&quality=96&sign=6c39d1c582e85c2c1ca31bc63a5e6c16&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "прогул", "коллега"]
    },
    "79": {
        "text": "Когда HR спрашивает о твоих ожиданиях по зарплате",
        "image_url": "https://sun9-54.userapi.com/impg/c857416/v857416070/fdeac/h_yDPKYpLe0.jpg?size=512x512&quality=96&sign=ae3c37beb6b8c90bc23cf2d16a3e4c20&type=album",
        "source": "hr_mem",
        "tags": ["офис", "зарплата", "собеседование"]
    },
    "80": {
        "text": "Когда кто-то принес торт в офис",
        "image_url": "https://sun9-47.userapi.com/impg/c857736/v857736502/c5b9e/_QwGp3VQqGE.jpg?size=720x540&quality=96&sign=bb89e3d0c5af74f4f695c551f6e9deb9&type=album",
        "source": "office_rat",
        "tags": ["офис", "торт", "еда"]
    },
    "81": {
        "text": "Когда узнал, что твоя бесплатная стажировка продлится ещё на месяц",
        "image_url": "https://sun9-31.userapi.com/impg/c853528/v853528726/1ba74c/z-2MZWpldcw.jpg?size=614x461&quality=96&sign=bbbacf9095c2c77a5ba43e81b7204a24&type=album",
        "source": "corporateethics",
        "tags": ["офис", "стажировка", "бесплатно"]
    },
    "82": {
        "text": "Когда увидел цены в столовой, и решил принести обед из дома",
        "image_url": "https://sun9-67.userapi.com/impg/c857220/v857220213/79ee0/kCRlbqKoKmw.jpg?size=1080x1080&quality=96&sign=7d3ebbbe1fc63bc12c0f3de0b7bf4d49&type=album",
        "source": "office_plankton",
        "tags": ["офис", "столовая", "обед"]
    },
    "83": {
        "text": "Чем ближе выходные, тем больше задач от начальника",
        "image_url": "https://sun9-16.userapi.com/impg/c852032/v852032432/1f29b9/vEbm1vYJ5iY.jpg?size=807x538&quality=96&sign=e5adcac84c3ffc2d7e0fa97387f0c0b9&type=album",
        "source": "the_working_day",
        "tags": ["офис", "пятница", "задачи"]
    },
    "84": {
        "text": "Когда отправил резюме, а они перезвонили через 5 минут",
        "image_url": "https://sun9-46.userapi.com/impg/c856416/v856416070/1947ba/mU6ELJQtNrI.jpg?size=1022x675&quality=96&sign=e87bc43a42bc6b10f43df72835b5c21c&type=album",
        "source": "hr_mem",
        "tags": ["офис", "резюме", "звонок"]
    },
    "85": {
        "text": "Когда директор вызывает тебя в кабинет, а ты не знаешь зачем",
        "image_url": "https://sun9-8.userapi.com/impg/c858024/v858024213/60a43/fMkbG3EoRdU.jpg?size=1032x774&quality=96&sign=c2b18ff95c8b0e9d9fcb5e9daa3c232f&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "директор", "вызов"]
    },
    "86": {
        "text": "Когда пришел на работу с радостным настроением, а там завал",
        "image_url": "https://sun9-60.userapi.com/impg/c854228/v854228069/1cf92c/znqW9-1R8ow.jpg?size=700x394&quality=96&sign=cef3defd1bc3e67db67ad4d839c8acb9&type=album",
        "source": "office_mems",
        "tags": ["офис", "настроение", "завал"]
    },
    "87": {
        "text": "Когда у тебя отдельный кабинет в опенспейсе",
        "image_url": "https://sun9-13.userapi.com/impg/c853328/v853328028/1b20cb/QaGvs7tJKlY.jpg?size=599x492&quality=96&sign=cf11b74f17fb69af883fbb40d5b68b97&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "опенспейс", "кабинет"]
    },
    "88": {
        "text": "Когда слышишь разговор о премиях в соседнем отделе",
        "image_url": "https://sun9-5.userapi.com/impg/c856132/v856132213/122f00/4jZW8_r8-OA.jpg?size=680x453&quality=96&sign=7dd8bf9ffe58c99991f8e82a93c2b07a&type=album",
        "source": "office_rat",
        "tags": ["офис", "премия", "подслушивание"]
    },
    "89": {
        "text": "Когда в резюме написал 'стрессоустойчивость', а на второй день работы уже хочешь уволиться",
        "image_url": "https://sun9-67.userapi.com/impg/c858336/v858336502/cbcc8/J62uOXBaZRM.jpg?size=600x600&quality=96&sign=0cd25cffd1d25d64ec20c5c8adc3d14e&type=album",
        "source": "corporateethics",
        "tags": ["офис", "стресс", "резюме"]
    },
    "90": {
        "text": "Когда начальник просит тебя поработать в выходные",
        "image_url": "https://sun9-42.userapi.com/impg/c855036/v855036502/1af1ba/1BYR7u6cwbQ.jpg?size=604x339&quality=96&sign=0566e24c5b58e82eefa743ca4ca954da&type=album",
        "source": "office_plankton",
        "tags": ["офис", "выходные", "начальник"]
    },
    "91": {
        "text": "Когда тебя просят поддержать инициативу начальства на собрании",
        "image_url": "https://sun9-12.userapi.com/impg/c855036/v855036888/1ac61e/yGWkj-EuwQ0.jpg?size=640x480&quality=96&sign=a32ab38c661a9a16b7d4a32b4afd20bb&type=album",
        "source": "the_working_day",
        "tags": ["офис", "собрание", "начальство"]
    },
    "92": {
        "text": "Когда не пишешь в рабочий чат 5 минут, а там уже 100 сообщений",
        "image_url": "https://sun9-38.userapi.com/impg/c858132/v858132997/a1c5d/cKnYvjuITXw.jpg?size=1196x884&quality=96&sign=7c23ecb75e20c3f40e2d4e93abc0a5ed&type=album",
        "source": "office_mems",
        "tags": ["офис", "чат", "сообщения"]
    },
    "93": {
        "text": "Когда уже 10 минут объясняешь проблему, а IT-специалист спрашивает «Вы пробовали перезагрузить?»",
        "image_url": "https://sun9-43.userapi.com/impg/c857724/v857724213/106c5c/5wWvxDfTBVc.jpg?size=600x600&quality=96&sign=4e3c8a32e1de5f99458cb9a77c87eaf4&type=album",
        "source": "zapiskibezdushi",
        "tags": ["офис", "IT", "перезагрузка"]
    },
    "94": {
        "text": "Когда единственный, кто понимает Excel в отделе",
        "image_url": "https://sun9-72.userapi.com/impg/c853528/v853528726/1baaa4/KLFdVs4tI6Y.jpg?size=636x900&quality=96&sign=77d37b0b5d3b19cee7d36d4e85d22ca1&type=album",
        "source": "workbench_mem",
        "tags": ["офис", "Excel", "навыки"]
    },
    "95": {
        "text": "Когда твой коллега берет больничный в пятницу и понедельник",
        "image_url": "https://sun9-28.userapi.com/impg/c855036/v855036213/243b41/FQiDxQq1RoI.jpg?size=600x587&quality=96&sign=e9ba07b8e252a6c6eec87bdb4b2ad2dd&type=album",
        "source": "hr_mem",
        "tags": ["офис", "больничный", "выходные"]
    },
    "96": {
        "text": "Когда шутишь в рабочем чате, а начальник ставит смайлик",
        "image_url": "https://sun9-71.userapi.com/impg/c857532/v857532616/c6e5e/kH8IhRNlOGw.jpg?size=750x416&quality=96&sign=1bc6bb4ba2b7a4a5461e1a8f4fad9d9a&type=album",
        "source": "office_rat",
        "tags": ["офис", "чат", "шутка"]
    },
    "97": {
        "text": "Когда начальник говорит, что сегодня важная встреча, а ты в джинсах",
        "image_url": "https://sun9-59.userapi.com/impg/c857332/v857332725/bb9e2/JYkWepq3QXY.jpg?size=750x601&quality=96&sign=27bd7d06ae0923c62a3cefa5f4a7e79b&type=album",
        "source": "corporateethics",
        "tags": ["офис", "дресс-код", "встреча"]
    },
    "98": {
        "text": "Когда два отдела выясняют, кто виноват в ошибке",
        "image_url": "https://sun9-57.userapi.com/impg/c855036/v855036502/1aedf3/n3WA71QdOgc.jpg?size=604x604&quality=96&sign=c0b77df62a5b44d5dd02b3fa5c3f7851&type=album",
        "source": "office_plankton",
        "tags": ["офис", "отделы", "ошибка"]
    },
    "99": {
        "text": "Когда ты новичок и хочешь произвести впечатление",
        "image_url": "https://sun9-19.userapi.com/impg/c858032/v858032502/ca6b0/jrOK0hVvW8M.jpg?size=600x315&quality=96&sign=79bd1c65c18d48a2bfaffe3292c14eda&type=album",
        "source": "the_working_day",
        "tags": ["офис", "новичок", "впечатление"]
    },
    "100": {
        "text": "Когда вся команда уже ушла с работы, а ты еще сидишь над отчетом",
        "image_url": "https://sun9-69.userapi.com/impg/c854332/v854332070/107f08/JUx4V6e-pnI.jpg?size=500x500&quality=96&sign=bb0c9bec1d18cf01e1c3c50baa9e11a5&type=album",
        "source": "office_mems",
        "tags": ["офис", "отчет", "задержка"]
    }
}

# Старая версия функции фильтрации заменена на новую из модуля content_filter
# Эта функция оставлена для обратной совместимости и просто вызывает новую функцию
def is_suitable_meme_deprecated(meme):
    """
    Проверяет, подходит ли мем для показа пользователю
    Отфильтровывает рекламные, спортивные мемы и другой нежелательный контент
    
    Эта функция устарела, используйте content_filter.is_suitable_meme
    """
    # Расширенный список запрещенных слов и тем для фильтрации мемов
    blacklist_words = [
        # Рекламные слова
        'реклама', 'рекламный', 'купить', 'скидка', 'акция', 'продажа', 'цена', 'подпишись',
        'заказать', 'закажи', 'клиент', 'товар', 'услуга', 'предложение', 'распродажа', 
        'выгодно', 'маркетинг', 'доставка', 'бизнес', 'продвижение', 'промокод', 'скидки',
        'магазин', 'аптека', 'шоппинг', 'телеграм канал', 'подпишитесь', 'только у нас',
        
        # Спортивные темы
        'спорт', 'футбол', 'хоккей', 'баскетбол', 'матч', 'чемпионат', 'турнир', 
        'соревнование', 'олимпиада', 'игра', 'тренировка', 'фитнес', 'тренер',
        'ставки', 'букмекер', 'тотализатор', 'прогноз', 'беттинг', 'команда',
        
        # Другие нежелательные темы
        'тренируйся', 'фитнес', 'зал', 'тренировка', 'клуб', 'абонемент', 'спортзал',
        'услуги', 'салон', 'nail', 'artist', 'маникюр', 'мастер', 'массаж'
    ]
    
    # URL и источники, которые нужно отфильтровать (узнаем рекламные картинки по URL)
    blacklist_domains = [
        'telegram-proxy', 'memepedia.ru', 'tiktok.com', 'instagram.com', 
        't.me/', 'telegram.me', 'vk.com/away', 'instagram', 'advert', 'ads', 
        'ggl.io', 'bit.ly', 'fb.me'
    ]
    
    # Проверяем изображение на наличие нежелательных источников
    if 'image_url' in meme:
        image_url = meme['image_url'].lower()
        if any(domain in image_url for domain in blacklist_domains):
            return False
        
        # Фильтруем по наличию ключевых слов в URL изображения
        if 'трен' in image_url.lower() or 'fitness' in image_url.lower():
            return False
        
        if 'nail' in image_url.lower() or 'маникюр' in image_url.lower():
            return False
    
    # Проверяем теги мема
    if 'tags' in meme:
        for tag in meme['tags']:
            tag_lower = tag.lower()
            if any(word in tag_lower for word in blacklist_words):
                return False
    
    # Проверяем текст мема
    if 'text' in meme:
        text_lower = meme['text'].lower()
        if any(word in text_lower for word in blacklist_words):
            return False
        
        # Дополнительная проверка на рекламу тренировок
        if 'тренируйся' in text_lower or 'тренируй' in text_lower:
            return False
            
    # Проверяем источник мема
    if 'source' in meme:
        source_lower = meme['source'].lower()
        if 'реклам' in source_lower or 'advert' in source_lower:
            return False
    
    return True
    
# Новая функция-обертка, которая использует модуль content_filter
def is_suitable_meme(meme):
    """
    Проверяет, подходит ли мем для показа пользователю
    Отфильтровывает рекламные, спортивные мемы и другой нежелательный контент
    
    Эта функция - обертка для content_filter.is_suitable_meme,
    оставлена для обратной совместимости
    """
    from content_filter import is_suitable_meme as filter_meme
    
    # Добавляем логирование для отладки
    result = filter_meme(meme)
    if not result:
        logger.info(f"Мем отфильтрован модулем content_filter: {meme.get('text', '')[:50]}...")
    
    return result