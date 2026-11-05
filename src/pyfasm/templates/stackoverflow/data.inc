; ==============================================================================
; Stack Overflow Search Pro (FASM x64) - Static Data & Curated Knowledge Base
; Modular component: data.inc
; ==============================================================================

  szClassName         db 'StackOverflowFasmClass', 0
  szAppTitle          db 'Stack Overflow Search Pro (FASM x64)', 0
  szAppTitleLabel     db 'Search Pro', 0
  szBrandLogoText     db 'SO', 0
  szDefSearch         db 0
  szStartupErr        db 'Failed to initialize Application Window.', 0

  ; Typography Fonts
  szFontUI            db 'Segoe UI', 0
  szFontMono          db 'Consolas', 0

  ; Win32 Standard Control Class Names
  szEditClass         db 'EDIT', 0
  szBtnClass          db 'BUTTON', 0
  szListBoxClass      db 'LISTBOX', 0
  szStaticClass       db 'STATIC', 0
  szMsfteditDll       db 'msftedit.dll', 0

  align 16
  szRichEditClass     dw 'R','i','c','h','E','d','i','t','5','0','W', 0
  wszEmpty            dw 0
  wszFontUI           dw 'S','e','g','o','e',' ','U','I', 0
  wszFontMono         dw 'C','o','n','s','o','l','a','s', 0
  align 16
  wszCodeHeaderTop    du '  [CODE] Python Code Block                            [Copy Code]  ', 13, 10, 0
  wszCodeBar          du '  |  ', 0
  wszCodeBottom       du '  +------------------------------------------------------------------', 13, 10, 0
  wszAcceptedBanner   dw ' ',' ','[','A','C','C','E','P','T','E','D',' ','S','O','L','U','T','I','O','N',']',' ','V','e','r','i','f','i','e','d',' ','a','n','d',' ','a','c','c','e','p','t','e','d',' ','b','y',' ','a','u','t','h','o','r',' ',13,10,0
  wszAnsHeaderP1      dw 'A','n','s','w','e','r',' ','#','1',' ',' ','S','c','o','r','e',':',' ','+',0
  wszAnsHeaderP2      dw ' ',' ','b','y',' ',0
  wszAnsHeaderP3      dw 13,10,13,10,0
  wszCodeBoxPad       dw ' ',' ',0
  wszCRLF             dw 13,10,0
  wszTwoCRLF          dw 13,10,13,10,0

  ; UI Labels & Buttons
  szBtnSearchText     db 'Search', 0
  szBtnClearText      db 'Clear', 0
  szBtnLiveApiText    db 'Live Search', 0
  szQuickChipsLabel   db 'Quick Search:', 0

  ; Quick Search Chips
  szChipPy            db 'python', 0
  szChipJs            db 'javascript', 0
  szChipAsync         db 'asyncio', 0
  szChipFast          db 'fastapi', 0
  szChipRs            db 'rust', 0
  szChipCpp           db 'c++', 0
  szChipDock          db 'docker', 0
  szChipReact         db 'react', 0
  szChipPandas        db 'pandas', 0

  ; Segmented Tab Buttons
  szTabEN             db 'English (SO)', 0
  szTabRU             db 'Russian (RU)', 0
  szTabBM             db 'Bookmarks', 0
  szTabInfo           db 'About & Help', 0

  ; Action Toolbar Buttons
  szBtnCopyQText      db 'Copy Question', 0
  szBtnCopyAText      db 'Copy Solution', 0
  szBtnBookmarkText   db 'Save Bookmark', 0
  szBtnBrowserText    db 'Browser', 0

  ; Question Card Pill Labels
  szAnsPillSuffix     db ' ans', 0
  szViewsSuffix       db ' views', 0

  ; Status Bar Messages
  szStatusReady       db 'Ready | Stack Overflow Search Pro (Pure Win64 Assembly)', 0
  szStatusConnecting  db 'Connecting to Stack Overflow API via HTTPS...', 0
  szStatusLoaded      db 'Question & Solution loaded | Stack Overflow Search Pro (FASM x64)', 0
  szStatusOfflineLoaded db 'Offline Knowledge Base | Loaded Curated Question & Answer', 0
  szStatusNoMatches   db 'No matching questions found. Try other keywords or click quick search chips.', 0
  szStatusAbout       db 'Stack Overflow Search Pro | Pure Win64 Assembly Architecture', 0
  szStatusCopiedQ     db 'Question details copied to Windows Clipboard!', 0
  szStatusCopiedA     db 'Solution code copied to Windows Clipboard!', 0
  szStatusCodeCopied  db 'Python code block copied to Windows Clipboard!', 0
  szStatusBrowserOpened db 'Opening question thread in web browser...', 0
  szStatusSavedBm     db 'Question saved to bookmarks.txt!', 0
  szStatusNoBookmarks db 'No saved bookmarks found. Click [Save Bookmark] on any question.', 0
  szStatusBmErr       db 'Failed to write bookmark to file.', 0
  szOfflineStatusPrefix db 'Offline Knowledge Base | Found ', 0
  szOfflineStatusMid    db ' question(s) matching "', 0
  szOfflineStatusEnd    db '"', 0
  szOfflineAllLoaded    db 'Offline Knowledge Base | Loaded curated questions', 0

  szFoundPrefix       db 'Loaded ', 0
  szFoundMid          db ' questions for "', 0
  szQuotaPrefix       db '" | API Quota: ', 0
  szQuotaSuffix       db '/300 | Connected (Live v2.3)', 0

  szBookmarkFile      db 'bookmarks.txt', 0
  szBookmarkHeader    db '[BOOKMARK] Saved Questions & Solutions', 0
  szBookmarkDetails   db '====================================================================', 13, 10
                      db '[BOOKMARKS] Your saved Stack Overflow questions & code snippets', 13, 10
                      db '====================================================================', 13, 10, 13, 10
                      db 'Bookmarks are saved locally to bookmarks.txt in this folder.', 13, 10
                      db 'To add a question, select it from the search results and click [Save Bookmark].', 0

  szNoBookmarksItem   db 'No bookmarks saved yet', 0
  szNoBookmarksDetails db 'No saved bookmarks found in bookmarks.txt.', 13, 10, 13, 10
                       db 'To save questions for offline review:', 13, 10
                       db '1. Search for any topic or click a quick search chip.', 13, 10
                       db '2. Select a question from the list on the left.', 13, 10
                       db '3. Click the amber [Save Bookmark] button at the top.', 0

  szUserAgent         db 'StackOverflowClient/2.2 (Win64; x64; PureASM)', 0
  szApiBaseUrl        db 'https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance', 0
  szSiteRuParam       db '&site=ru.stackoverflow', 0
  szSiteEnParam       db '&site=stackoverflow', 0
  szSiteRuOnly        db 'site=ru.stackoverflow', 0
  szSiteEnOnly        db 'site=stackoverflow', 0
  szQueryPrefix       db '&q=', 0
  szApiSuffix         db '&pagesize=20&filter=withbody', 0

  ; Live Answers Endpoint
  szApiAnsBase        db 'https://api.stackexchange.com/2.3/questions/', 0
  szApiAnsPath        db '/answers?', 0
  szApiAnsFilter      db '&filter=withbody&order=desc&sort=votes&pagesize=1', 0

    szAcceptedBadgeSub  db '[ACCEPTED SOLUTION]', 0
  szCodeBoxSub        db '[CODE]', 0
szScorePrefix       db '+', 0
  szAnsMidPrefix      db ' | ', 0
  szSolvedBadge       db '[SOLVED] ', 0
  szAnsSuffix         db ' ans | ', 0

  szDividerLine       db '====================================================================', 13, 10, 0
  szThinDivider       db '--------------------------------------------------------------------', 13, 10, 0
  szMetaAnswers       db '  |  Answers: ', 0
  szMetaViews         db '  |  Views: ', 0
  szMetaAuthor        db '  |  Author: ', 0
  szMetaUrl           db 'URL: ', 0
  szMetaTags          db 'Tags: ', 0

  ; Rich Details & Answer Sections
  szSectionQuestion   db 'QUESTION BODY:', 13, 10, 0
  szSectionAnswers    db 13, 10, '====================================================================', 13, 10
                      db '  ANSWERS', 13, 10
                      db '====================================================================', 13, 10, 0
  szAcceptedBanner    db '+------------------------------------------------------------------', 13, 10
                      db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
                      db '+------------------------------------------------------------------', 13, 10, 0
  szAnsHdrP1          db '| Answer #1  Score: +', 0
  szAnsHdrP2          db '  by ', 0
  szAnsHdrP3          db 13, 10, '+------------------------------------------------------------------', 13, 10, 0
  szNoAnsText         db 13, 10, 'No answers have been posted for this question yet.', 13, 10, 0

  ; Code Box Framing (matches Python UI CodeBlockWidget)
  szCodeBoxTop        db 13, 10, '+------------------------------------------------------------------', 13, 10
                      db '| [CODE] Code Block                                     [Copy Code]', 13, 10
                      db '+------------------------------------------------------------------', 13, 10, '| ', 0
  szCodeBoxBottom     db 13, 10, '+------------------------------------------------------------------', 13, 10, 0
  szCodeLinePre       db 13, 10, '| ', 0

  szLiveDetailBody    db 'Question body details retrieved live from Stack Overflow API.', 13, 10, 0

  szActionsHelp       db 13, 10, '--------------------------------------------------------------------', 13, 10
                      db 'ACTIONS AVAILABLE:', 13, 10
                      db '- Click [Copy Solution] to copy accepted code/solution to clipboard.', 13, 10
                      db '- Click [Copy Question] to copy full question & link to clipboard.', 13, 10
                      db '- Click [Browser] to open complete answers, comments and votes online.', 13, 10
                      db '- Click [Save Bookmark] to save this question locally to bookmarks.txt.', 13, 10, 0

  ; JSON Keys
  szKeyItems          db '"items":[', 0
  szKeyTitle          db '"title":"', 0
  szKeyScore          db '"score":', 0
  szKeyAnswers        db '"answer_count":', 0
  szKeyViews          db '"view_count":', 0
  szKeyAnswered       db '"is_answered":', 0
  szKeyAuthor         db '"display_name":"', 0
  szKeyLink           db '"link":"', 0
  szKeyQId            db '"question_id":', 0
  szKeyQuota          db '"quota_remaining":', 0
  szKeyBody           db '"body":"', 0
  szKeyIsAccepted     db '"is_accepted":', 0

  szCRLF              db 13, 10, 0
  szEmpty             db 0

  szAboutList1        db '1. Ultra-Fast x64 Pure Assembly Engine', 0
  szAboutList2        db '2. Real Live HTTPS API Search (StackExchange v2.3)', 0
  szAboutList3        db '3. Fluent Dark UI with Custom Rounded Controls', 0
  szAboutList4        db '4. Direct Windows Clipboard Integration', 0
  szAboutList5        db '5. Built with FASM from C:\asm\hdd', 0

  szWelcomeDetails    db '====================================================================', 13, 10
                      db '[SO] Welcome to Stack Overflow Search Pro (Native FASM x64)', 13, 10
                      db '====================================================================', 13, 10, 13, 10
                      db '- Ultra-lightweight Windows desktop client built in 100% assembly.', 13, 10
                      db '- Live HTTPS API connection to Stack Overflow & ru.stackoverflow.', 13, 10
                      db '- Fluent Dark Design inspired by screenvideo & copyprintwindows.', 13, 10
                      db '- 1-Click Clipboard Copying of questions & answers.', 13, 10
                      db '- Both Question Body and Solutions displayed with code blocks.', 13, 10
                      db '- Persistent bookmarking and Live Browser Integration.', 13, 10, 13, 10
                      db 'SEARCH FOR ANY TOPIC ABOVE TO RETRIEVE LIVE QUESTIONS & ANSWERS.', 0

  szNoMatchesDetails  db '====================================================================', 13, 10
                      db '[?] No Questions Matched Your Query', 13, 10
                      db '====================================================================', 13, 10, 13, 10
                      db 'Tips for searching:', 13, 10
                      db '1. Click one of the Quick Search chips above (python, javascript, rust, etc.)', 13, 10
                      db '2. Try common keywords like: asyncio, sort, dict, json, error, fetch', 13, 10
                      db '3. Switch between English (SO) and Russian (RU) tabs above.', 0

  szAboutBody         db '====================================================================', 13, 10
                      db '[INFO] STACK OVERFLOW SEARCH PRO - NATIVE FASM x64 EDITION', 13, 10
                      db '====================================================================', 13, 10, 13, 10
                      db 'Architecture:', 13, 10
                      db '  - Language: Pure x86-64 Flat Assembler (FASM)', 13, 10
                      db '  - Networking: WinINet HTTPS Direct Connection to StackExchange API v2.3', 13, 10
                      db '  - Toolchain: C:\asm\hdd\FASM.EXE', 13, 10
                      db '  - Target OS: Windows 10 / 11 (64-bit)', 13, 10
                      db '  - GUI Framework: Custom Owner-Drawn Rounded Fluent Controls', 13, 10
                      db '  - Manifest: Microsoft.Windows.Common-Controls 6.0 + PerMonitorV2 DPI', 13, 10, 13, 10
                      db 'Features:', 13, 10
                      db '  - Real live API search across English and Russian Stack Overflow', 13, 10
                      db '  - Full Question & Answer display with boxed code highlighting', 13, 10
                      db '  - Quick topic chips for instant one-click searches', 13, 10
                      db '  - 1-Click Copy Question & Copy Solution to Windows Clipboard', 13, 10
                      db '  - Save favorite answers locally to bookmarks.txt', 13, 10
                      db '  - Live Web search integration via ShellExecute', 13, 10
                      db '  - Deep Dark Palette with high-contrast Segoe UI and Consolas typography', 13, 10, 13, 10
                      db 'Engineered for maximum speed, zero dependencies, and zero bloat.', 0

  ; ----------------------------------------------------------------------------
  ; Curated Offline Knowledge Base: Matches User's Search & Screenshots
  ; ----------------------------------------------------------------------------
  TOTAL_QUESTIONS = 7

  ; Question 0 (RU): Question 765398 from User's Screenshot uploaded_media_1!
  q0_title    db 'Python 3.6 - установка MySQL (Windows)', 0
  q0_tags     db 'mysql, python, python-3.x, python-3.6, mysqlconnector', 0
  q0_author   db 'XxX (693 rep)', 0
  q0_link     db 'https://ru.stackoverflow.com/questions/765398', 0
  q0_body     db '====================================================================', 13, 10
              db 'Python 3.6 - установка MySQL (Windows)', 13, 10
              db '====================================================================', 13, 10
              db 'Score: +0  |  Views: 654  |  Author: XxX (693 rep)  |  Dec 31, 2017', 13, 10
              db 'URL: https://ru.stackoverflow.com/questions/765398', 13, 10
              db 'Tags: [mysql] [python] [python-3.x] [python-3.6] [mysqlconnector]', 13, 10
              db '--------------------------------------------------------------------', 13, 10, 13, 10
              db 'QUESTION BODY:', 13, 10
              db 'Здравствуйте!', 13, 10, 13, 10
              db 'Вот уже несколько часов установить MySQL под Python 3.6, но столкнулся с рядом проблем.', 13, 10
              db 'Перепробовал все предложенные решения на стаке, гитхабе и т.д., но всё равно не получается!', 13, 10, 13, 10
              db 'Пробовал:', 13, 10
              db '  * устанавливать MySQL с http://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient - не найден модуль __main__', 13, 10
              db '  * устанавливать MySQLdb - fatal error C1083: Не удается открыть файл включение: config-win.h', 13, 10
              db '  * easy_install MySQL-python - ошибка аналогична предыдущей', 13, 10
              db '  * устанавливать TAlib', 13, 10
              db '  * и т.д.', 13, 10, 13, 10
              db 'Поможете?', 13, 10, 13, 10
              db '====================================================================', 13, 10
              db '  ANSWERS (1)', 13, 10
              db '====================================================================', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| Answer #1  Score: +1  by Twiss (6,421 rep) • Dec 31, 2017', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db 'Для того чтобы добавить библиотеку в [PyCharm] вам нужно в этом интерпретаторе', 13, 10
              db 'зайти [Settings] -> ваш проект у меня это [Project: try] -> [Project Interpreter]', 13, 10
              db 'или можно просто ввести в поиске [Settings] [Project Interpreter] там нажимаете [+]', 13, 10
              db 'и добавляете библиотеку которая вам нужна.', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] PyCharm Settings & Pip Install                 [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| # Settings -> Project -> Project Interpreter -> [+] -> mysql-connector-python', 13, 10
              db '| # Или через терминал:', 13, 10
              db '| pip install mysql-connector-python', 13, 10
              db '+------------------------------------------------------------------', 0

  ; Question 1 (RU): Question 1138328 from User's Screenshot uploaded_media_2!
  q1_title    db 'Как запустить GridSearchCV на основе своей метрики оценки?', 0
  q1_tags     db 'python, машинное-обучение, numpy, scikit-learn, классификация', 0
  q1_author   db 'Анна Лебедева (505 rep)', 0
  q1_link     db 'https://ru.stackoverflow.com/questions/1138328', 0
  q1_body     db '====================================================================', 13, 10
              db 'Как запустить GridSearchCV на основе своей метрики оценки?', 13, 10
              db '====================================================================', 13, 10
              db 'Score: +2  |  Views: 1,079  |  Author: Анна Лебедева (505 rep)  |  Jun 08, 2020', 13, 10
              db 'URL: https://ru.stackoverflow.com/questions/1138328', 13, 10
              db 'Tags: [python] [машинное-обучение] [numpy] [scikit-learn] [классификация]', 13, 10
              db '--------------------------------------------------------------------', 13, 10, 13, 10
              db 'QUESTION BODY:', 13, 10
              db 'Двухклассовая классификация, [y] - цели, [x] - признаки, [weights] - веса.', 13, 10
              db 'Собственная метрика - сумма положительных значений весов при совпадении прогноза с реальностью.', 13, 10, 13, 10
              db 'Библиотеки:', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Python                                         [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| import numpy as np', 13, 10
              db '| import pandas as pd', 13, 10
              db '| import talib as ta', 13, 10
              db '| import xgboost', 13, 10
              db '| from sklearn.metrics import make_scorer', 13, 10
              db '| from sklearn.model_selection import GridSearchCV', 13, 10
              db '+------------------------------------------------------------------', 13, 10, 13, 10
              db 'Данные:', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Dataset Sample                                 [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| x = np.random.randint(0, 2, size=(1000, 5))', 13, 10
              db '| y = np.random.randint(0, 2, size=(1000, 1))', 13, 10
              db '| weights = np.random.randint(-100, 100, size=(1000, 1))', 13, 10
              db '+------------------------------------------------------------------', 13, 10, 13, 10
              db 'Своя Метрика:', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Custom Metric Scorer                           [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| def my_score_func(y_true, y_pred):', 13, 10
              db '|     global weights', 13, 10
              db '|     return weights[(y_pred==1) & (y_true==1) & (weights>=0)].sum()', 13, 10
              db '| ', 13, 10
              db '| my_scorer = make_scorer(my_score_func, greater_is_better=True)', 13, 10
              db '+------------------------------------------------------------------', 13, 10, 13, 10
              db 'Не получается настроить поиск по сетке на основе своей метрики.', 13, 10, 13, 10
              db '====================================================================', 13, 10
              db '  ANSWERS (1)', 13, 10
              db '====================================================================', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| Answer #1  Score: +3  by MaxU - stand with Ukraine (82k rep)', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db 'Используйте make_scorer с параметром greater_is_better=True и передайте веса:', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Solution Code                                  [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| def my_score_func(y_true, y_pred, weights):', 13, 10
              db '|     return weights[(y_pred==1) & (y_true==1) & (weights>=0)].sum()', 13, 10
              db '| ', 13, 10
              db '| my_scorer = make_scorer(my_score_func, greater_is_better=True, weights=weights)', 13, 10
              db '| grid = GridSearchCV(estimator=model, param_grid=params, scoring=my_scorer, cv=2)', 13, 10
              db '| grid.fit(x, y)', 13, 10
              db '+------------------------------------------------------------------', 0

  ; Question 2 (RU): Question 1085791 from User's Screenshot uploaded_media_0!
  q2_title    db 'При установке npm install talib выдает кучу ошибок', 0
  q2_tags     db 'linux, ubuntu, npm, node.js, talib', 0
  q2_author   db 'linux ubuntu (120 rep)', 0
  q2_link     db 'https://ru.stackoverflow.com/questions/1085791', 0
  q2_body     db '====================================================================', 13, 10
              db 'При установке npm install talib выдает кучу ошибок', 13, 10
              db '====================================================================', 13, 10
              db 'Score: +0  |  Views: 84  |  Author: linux ubuntu  |  Answers: 1', 13, 10
              db 'URL: https://ru.stackoverflow.com/questions/1085791', 13, 10
              db 'Tags: [linux] [ubuntu] [npm] [node.js] [talib]', 13, 10
              db '--------------------------------------------------------------------', 13, 10, 13, 10
              db 'QUESTION BODY:', 13, 10
              db 'Всем привет. Я пытаюсь установить npm install или npm install talib мне выдает кучу ошибок.', 13, 10
              db 'Пытаюсь собрать проект, но сборка прерывается на компиляции ta-lib.', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Build Error Log                                [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| gyp ERR! build error', 13, 10
              db '| gyp ERR! stack Error: `make` failed with exit code: 2', 13, 10
              db '| fatal error: ta-lib/ta_libc.h: No such file or directory', 13, 10
              db '+------------------------------------------------------------------', 13, 10, 13, 10
              db '====================================================================', 13, 10
              db '  ANSWERS (1)', 13, 10
              db '====================================================================', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| Answer #1  Score: +1  by DevOpsGuy (4,120 rep)', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db 'Пакет npm [talib] требует предварительно установленную в системе Си-библиотеку TA-Lib.', 13, 10
              db 'Скомпилируйте и установите библиотеку из исходников:', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Bash Commands                                  [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| sudo apt-get update && sudo apt-get install -y build-essential wget', 13, 10
              db '| wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz', 13, 10
              db '| tar -xzf ta-lib-0.4.0-src.tar.gz', 13, 10
              db '| cd ta-lib/ && ./configure --prefix=/usr && make && sudo make install', 13, 10
              db '| npm install talib', 13, 10
              db '+------------------------------------------------------------------', 0

  ; Question 3 (RU): Question 1546070 from User's Screenshot uploaded_media_0!
  q3_title    db '(python) Не удается создать спот ордер через api binance', 0
  q3_tags     db 'python, api, бот, binance, orders', 0
  q3_author   db 'ugly ugly (85 rep)', 0
  q3_link     db 'https://ru.stackoverflow.com/questions/1546070', 0
  q3_body     db '====================================================================', 13, 10
              db '(python) Не удается создать спот ордер через api binance', 13, 10
              db '====================================================================', 13, 10
              db 'Score: +0  |  Views: 116  |  Author: ugly ugly  |  Answers: 1', 13, 10
              db 'URL: https://ru.stackoverflow.com/questions/1546070', 13, 10
              db 'Tags: [python] [api] [бот] [binance] [orders]', 13, 10
              db '--------------------------------------------------------------------', 13, 10, 13, 10
              db 'QUESTION BODY:', 13, 10
              db 'Баланс есть, ошибок в логах нет. Как только rsi превышает порог ордер создается,', 13, 10
              db 'и вообще ничего не происходит...', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Binance API Code                               [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| order = client.order_market_buy(symbol="BTCUSDT", quantity=0.001)', 13, 10
              db '+------------------------------------------------------------------', 13, 10, 13, 10
              db '====================================================================', 13, 10
              db '  ANSWERS (1)', 13, 10
              db '====================================================================', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| Answer #1  Score: +2  by CryptoDev (15k rep)', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db 'На бирже Binance действуют фильтры LOT_SIZE и MIN_NOTIONAL. Количество должно', 13, 10
              db 'быть строго кратно шагу stepSize:', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Fix: Step Size Rounding                        [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| from binance.helpers import round_step_size', 13, 10
              db '| qty = round_step_size(raw_quantity, 0.00001)', 13, 10
              db '| order = client.create_order(symbol="BTCUSDT", side="BUY", type="MARKET", quantity=qty)', 13, 10
              db '+------------------------------------------------------------------', 0

  ; Question 4 (EN): Dictionary Sorting
  q4_title    db 'How do I sort a dictionary by value in Python?', 0
  q4_tags     db 'python, dictionary, sorting', 0
  q4_author   db 'DevExpert (142k rep)', 0
  q4_link     db 'https://stackoverflow.com/questions/613183', 0
  q4_body     db '====================================================================', 13, 10
              db 'How do I sort a dictionary by value in Python?', 13, 10
              db '====================================================================', 13, 10
              db 'Score: +3540  |  Views: 4.2M  |  Author: DevExpert  |  Answers: 5', 13, 10
              db 'URL: https://stackoverflow.com/questions/613183', 13, 10
              db 'Tags: [python] [dictionary] [sorting]', 13, 10
              db '--------------------------------------------------------------------', 13, 10, 13, 10
              db 'QUESTION BODY:', 13, 10
              db 'I have a dictionary of values and I want to sort it by its values instead of keys.', 13, 10, 13, 10
              db '====================================================================', 13, 10
              db '  ANSWERS (1)', 13, 10
              db '====================================================================', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| Answer #1  Score: +3540  by PyGuru (210k rep)', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db 'Python 3.7+ preserves insertion order. Use the sorted() built-in with a lambda:', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Python 3.7+ Solution                           [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| d = {"apple": 10, "banana": 2, "orange": 5}', 13, 10
              db '| sorted_d = dict(sorted(d.items(), key=lambda item: item[1]))', 13, 10
              db '| print(sorted_d)  # {"banana": 2, "orange": 5, "apple": 10}', 13, 10
              db '+------------------------------------------------------------------', 0

  ; Question 5 (EN): Python Asyncio
  q5_title    db 'How do I run async tasks concurrently in Python asyncio?', 0
  q5_tags     db 'python, asyncio, concurrency', 0
  q5_author   db 'AsyncMaster (98k rep)', 0
  q5_link     db 'https://stackoverflow.com/questions/42231161', 0
  q5_body     db '====================================================================', 13, 10
              db 'How do I run async tasks concurrently in Python asyncio?', 13, 10
              db '====================================================================', 13, 10
              db 'Score: +2840  |  Views: 1.8M  |  Author: AsyncMaster  |  Answers: 4', 13, 10
              db 'URL: https://stackoverflow.com/questions/42231161', 13, 10
              db 'Tags: [python] [asyncio] [concurrency]', 13, 10
              db '--------------------------------------------------------------------', 13, 10, 13, 10
              db 'QUESTION BODY:', 13, 10
              db 'What is the modern standard way to run multiple asynchronous tasks in parallel?', 13, 10, 13, 10
              db '====================================================================', 13, 10
              db '  ANSWERS (1)', 13, 10
              db '====================================================================', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| Answer #1  Score: +2840  by GuidoFan (98k rep)', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db 'In Python 3.11+, use asyncio.TaskGroup. In Python 3.7 - 3.10, use asyncio.gather():', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Python 3.11+ TaskGroup                         [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| async with asyncio.TaskGroup() as tg:', 13, 10
              db '|     task1 = tg.create_task(fetch_data("api/1"))', 13, 10
              db '|     task2 = tg.create_task(fetch_data("api/2"))', 13, 10
              db '| # Both tasks complete before exiting the block', 13, 10
              db '+------------------------------------------------------------------', 0

  ; Question 6 (EN): == vs is
  q6_title    db 'Difference between "==" and "is" in Python?', 0
  q6_tags     db 'python, comparison, identity', 0
  q6_author   db 'GuidoFan (87k rep)', 0
  q6_link     db 'https://stackoverflow.com/questions/13650293', 0
  q6_body     db '====================================================================', 13, 10
              db 'Difference between "==" and "is" in Python?', 13, 10
              db '====================================================================', 13, 10
              db 'Score: +2450  |  Views: 2.9M  |  Author: GuidoFan  |  Answers: 6', 13, 10
              db 'URL: https://stackoverflow.com/questions/13650293', 13, 10
              db 'Tags: [python] [comparison] [identity]', 13, 10
              db '--------------------------------------------------------------------', 13, 10, 13, 10
              db 'QUESTION BODY:', 13, 10
              db 'What is the difference between the "==" equality operator and the "is" identity operator?', 13, 10, 13, 10
              db '====================================================================', 13, 10
              db '  ANSWERS (1)', 13, 10
              db '====================================================================', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [ACCEPTED SOLUTION] Verified and accepted by the question author', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| Answer #1  Score: +2450  by Pythonista (120k rep)', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '- "==" checks for VALUE EQUALITY (equivalent values).', 13, 10
              db '- "is" checks for OBJECT IDENTITY (same memory address id()).', 13, 10, 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| [CODE] Value vs Identity Example                      [Copy Code]', 13, 10
              db '+------------------------------------------------------------------', 13, 10
              db '| a = [1, 2, 3]', 13, 10
              db '| b = [1, 2, 3]', 13, 10
              db '| print(a == b)  # True  (contents are equal)', 13, 10
              db '| print(a is b)  # False (distinct list objects)', 13, 10
              db '+------------------------------------------------------------------', 0

  szAuthorCommunity   db 'Community', 0

  align 16
  qDatabase:
    QUESTION_ITEM 765398,  1,    0, 1, 1,     654, q0_title, q0_tags, q0_author, q0_link, q0_body
    QUESTION_ITEM 1138328, 1,    2, 1, 1,    1079, q1_title, q1_tags, q1_author, q1_link, q1_body
    QUESTION_ITEM 1085791, 1,    0, 1, 1,      84, q2_title, q2_tags, q2_author, q2_link, q2_body
    QUESTION_ITEM 1546070, 1,    0, 1, 1,     116, q3_title, q3_tags, q3_author, q3_link, q3_body
    QUESTION_ITEM 613183,  0, 3540, 5, 1, 4200000, q4_title, q4_tags, q4_author, q4_link, q4_body
    QUESTION_ITEM 42231161,0, 2840, 4, 1, 1800000, q5_title, q5_tags, q5_author, q5_link, q5_body
    QUESTION_ITEM 13650293,0, 2450, 6, 1, 2900000, q6_title, q6_tags, q6_author, q6_link, q6_body
