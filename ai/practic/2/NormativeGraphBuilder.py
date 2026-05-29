# 📦 Скрипт: Парсинг нормативных документов в Graph-Ready JSON
import re
from dataclasses import dataclass, asdict
import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from markdown_it import MarkdownIt
from enum import Enum

# 🔹 1. Структура узла графа знаний
@dataclass
class NormativeNode:
    id: str
    type: str  # order, appendix, section, clause, amendment_order, form
    parent_id: Optional[str] = None
    valid_from: str = "2000-01-01"
    valid_to: Optional[str] = None
    source_file: Optional[str] = None
    title: Optional[str] = None
    heading: Optional[str] = None
    text: Optional[str] = None
    clause_num: Optional[str] = None
    change_status: Optional[str] = None
    change_type: Optional[str] = None
    amends_clause: Optional[str] = None
    formulas: Optional[List[str]] = None
    structure: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Экспорт в dict для JSON-сериализации (фильтрует None)"""
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class Department:
    name: str = None
    fullname: str = None

@dataclass
class Signer:
    position: str = None
    shortname: str = None
    
@dataclass
class Registration:
    department: Department
    number: int
    date: date

@dataclass
class DocumentSet:
    id: str
    domain: str
    base_order: Optional[str] = None
    latest_amendment: Optional[str] = None
    last_updated: Optional[date] = None
    publisher: Optional[Department] = None

    def to_dict(self) -> Dict[str, Any]:
        """Экспорт в dict для JSON-сериализации (фильтрует None)"""
        return {k: v for k, v in asdict(self).items() if v is not None}

class NormativeGraphBuilder:
    def __init__(self):
        self.nodes: List[Dict[str, NormativeNode]] = []
        self.doc: DocumentSet = {}

    def _clean_id(self, text: str) -> str:
        """Безопасный ID для графа: только буквы, цифры, _"""
        return re.sub(r'[^a-zA-Zа-яА-Я0-9_]', '_', text.strip().lower())[:50]

    def _parse_date(self, d: str) -> Optional[str]:
        """DD.MM.YYYY -> YYYY-MM-DD"""
        try:
            return date.strptime(d.strip(), "%d.%m.%Y").strftime("%Y-%m-%d")
        except:
            return None

    def _add_node(self, **kwargs) -> str:
        node = {
            "id": kwargs.get("id"),
            "type": kwargs.get("type", "section"),
            "parent_id": kwargs.get("parent_id"),
            "valid_from": kwargs.get("valid_from"),
            "valid_to": kwargs.get("valid_to"),
            "source_file": kwargs.get("source_file"),
        }
        # Добавляем только непустые поля
        for k, v in kwargs.items():
            if k not in node and v is not None:
                node[k] = v
        if not node["id"]:
            node["id"] = self._clean_id(node.get("title", node.get("heading", "unknown"))) + f"_{date.now().timestamp()}"
        self.nodes.append(node)
        return node["id"]

    def parse_filename(self, filename: str):# -> tuple[str, str, str] : 
        """
        Безопасно парсит имя файла нормативного документа и извлекает метаданные.
        
        Ожидаемый формат: {ведомство}_{дата}_{тип}_{номер}_{содержание?}.md
        Примеры:
        - minstroy_20200804_pr_421_data.md
        - minstroy_20220707_pr_557-421_add-1.md
        - minstroy_20200804_pr_421.md (сам приказ без суффикса)

        Возвращает order_id и тип содержимого, ошибку в случае провала
        """

        # 1. Нормализация имени
        clean_name = Path(filename).name.strip()
        if clean_name.lower().endswith(".md"):
            clean_name = clean_name[:-3]
            
        parts = [p for p in clean_name.split("_") if p]  # фильтруем пустые из двойных __
    
        if len(parts) < 4:
            return  ("", "", f"Недостаточно сегментов: ожидалось >=4, получено {len(parts)}, filename: {filename}")
        
        # 2. Базовое извлечение
        self.department = parts[0].lower()
        self.date_raw = parts[1]
        self.doc_type = parts[2].lower()
        self.number_raw = parts[3]
        self.data_type = parts[4].lower() if len(parts) > 4 else ""

        # id =  str.join("_", [department, date_raw, doc_type, number_raw])
        # return (id, content_type, None)
    
    def _is_base_order(self) -> bool:
        return self.number_raw.find("-") == -1
    
    def parse_content(self, content: str):
        if self.data_type == "":
            self.parse_order(content)
        # if data_type == "data":
        #     node.parse_data(content)
        # if data_type == "add":
        #     node.parse_add(content)
        # if data_type.startswith("add-"):
        #     node.parse_addplus(content)

    def parse_order(self, content: str) -> str:
        """Парсит приказ (метаданные + текст приказа)"""
        lines = content.split('\n')
        meta = {}
        desc_lines = []
        data_lines = []

        class Head(Enum):
            Undefined = "undefined"
            META = "meta"
            DESC = "desc"
            DATA = "data"

        active_head = Head.Undefined
        parent_id = str
        
        for line in lines:
            if line.strip().startswith('# Свойства'):
                active_head = Head.META
                continue
            if line.strip().startswith("# Описание"):
                active_head = Head.DESC
                continue
            if line.strip().startswith("# Содержание"):
                active_head = Head.DATA
                continue
            if line.strip().startswith('#'):
                active_head = Head.Undefined                
                print("undefined_data: ", line)
                continue
            else:
                match active_head:
                    case Head.META:
                        # Разбор пар "ключ значение" или "ключ: значение"
                        m = re.match(r'^([^\s:]+)\s*[:\s]+(.*)', line)
                        if m:
                            meta[m.group(1)] = m.group(2).strip()
                    case Head.DESC:
                        desc_lines.append(line)
                    case Head.DATA:
                        data_lines.append(line)
                    case Head.Undefined:
                        print("undefined_data: ", line)

        department = Department(meta.get("ВедомствоСокращенно") ,meta.get("Ведомство"))
        pub_num = meta.get("номерПубликации")
        pub_date = datetime.strptime(meta.get("датаПубликации","01.01.2000") ,'%d.%m.%Y').date()
        if self._is_base_order(): 
            if self.doc.base_order == None:
                self.doc.base_order = pub_num
                self.doc.latest_amendment = pub_num
                self.doc.publisher = department
        else:
            parent_number_raw = str.join("-", self.number_raw.split("-")[1:])
            parent_id = str.join("_", [self.department, self.date_raw, self.doc_type, parent_number_raw])
            if self.doc.last_updated is None or self.doc.last_updated < pub_date:
                self.doc.latest_amendment = pub_num
                self.doc.last_updated = pub_date
        
        # self.doc_id_map[filename] = doc_id

        doc_id = str.join("_", [self.department, self.date_raw, self.doc_type, self.number_raw])
        self._add_node(
            id=doc_id,
            type="order",
            number=meta.get("номер"),
            city=meta.get("город"),
            date=datetime.strptime(meta.get("дата","01.01.2000") ,'%d.%m.%Y').date(),            
            publisher=department if self.department != department else None,
            signer=Signer(meta.get("ПодписантДолжность"), meta.get("Подписант")),
            status=meta.get("статус"),
            registration=Registration(
                department=Department(fullname=meta.get("ВедомствоРегистратор")),
                number=meta.get("номерРегистрации"), 
                date=datetime.strptime(meta.get("датаРегистрации","01.01.2000") ,'%d.%m.%Y').date()),
            desription="\n".join(desc_lines),
            data="\n".join(data_lines),
            valid_from=datetime.strptime(meta.get("вступаетВДействиеС","01.01.2000") ,'%d.%m.%Y').date(),
            valid_to=None,
            parent_id=parent_id
        )
        return doc_id

    def parse_base_methodology(self, content: str, filename: str, parent_order_id: str, valid_from: str):
        """Парсит основную методику: разделы (I., II.) -> пункты (1., 2., 10а)"""
        self._add_node(
            id=f"{parent_order_id}_data",
            type="appendix",
            title="Основная методика",
            parent_id=parent_order_id,
            valid_from=valid_from, valid_to=None, source_file=filename
        )

        # Разбиваем по разделам (I., II., III.)
        sections = re.split(r'\n(?=[IVX]+\.\s)', content)
        for sec_text in sections:
            sec_match = re.match(r'^([IVX]+)\.\s*(.+?)(?=\n|\Z)', sec_text.strip())
            if not sec_match: continue
            sec_num, sec_title = sec_match.groups()
            sec_id = f"{parent_order_id}_data::sec_{sec_num.lower()}"
            
            self._add_node(
                id=sec_id, type="section", heading=sec_title.strip(),
                parent_id=f"{parent_order_id}_data", valid_from=valid_from, valid_to=None, source_file=filename
            )

            # Разбиваем по пунктам внутри раздела
            # Паттерн: "1. ", "10а. ", "10.б ", "52.1. "
            clause_re = re.compile(r'^\s*([0-9а-яё]+(?:\.[0-9а-яё]+)*[\.\)]?)\s+(.*)', re.MULTILINE | re.IGNORECASE)
            for m in clause_re.finditer(sec_text):
                c_num, c_text = m.group(1).strip().rstrip('.'), m.group(2).strip()
                if not c_text or len(c_text) < 5: continue
                
                # Извлекаем формулы $$ ... $$
                formulas = re.findall(r'\$\$(.*?)\$\$', c_text, re.DOTALL)
                clean_text = re.sub(r'\$\$(.*?)\$\$', '[FORMULA_REF]', c_text, flags=re.DOTALL)
                
                c_id = f"{sec_id}::clause::{c_num}"
                self._add_node(
                    id=c_id, type="clause", clause_num=c_num, text=clean_text,
                    parent_id=sec_id, valid_from=valid_from, valid_to=None, source_file=filename,
                    formulas=[f.strip() for f in formulas] if formulas else None
                )

    def parse_amendments(self, content: str, filename: str, base_order_id: str, valid_from: str):
        amend_doc_id = f"{base_order_id}_amend_{self._clean_id(valid_from)}"
        self._add_node(
            id=amend_doc_id, type="amendment_order", title="Текст изменений",
            parent_id=None, valid_from=valid_from, valid_to=None, source_file=filename,
            meta={"amends_doc": base_order_id}
        )

        # Устойчивые паттерны, игнорирующие артефакты OCR: «», "", >», ., \n
        patterns = [
            # Пункт X изложить в следующей редакции: «...»
            (r'Пункт\s+([^\s:;,]+)\s+изложить\s+в\s+следующей\s+редакции[:\s]+[«""]?\s*(.*?)(?=\s*>?\s*[»""][\.\s]*(?:\n|$))', 'replace'),
            # В пункте X слова ... заменить словами ...
            (r'В пункте\s+([^\s:;,]+)\s+слова\s+[«""]?(.*?)[»""]?\s+заменить\s+словами\s+[«""]?(.*?)[»""]?', 'modify'),
            # Дополнить пунктом X следующего содержания: ...
            (r'Дополнить\s+пунктом\s+([^\s:;,]+)\s+следующего\s+содержания[:\s]+(.*?)(?=\n\s*(?:Дополнить|В пункте|Пункт|Абзац|Примечание)|\Z)', 'add'),
            # Абзац ... пункта X изложить в следующей редакции: ...
            (r'Абзац\s+(.+?)\s+пункта\s+([^\s:;,]+)\s+изложить\s+в\s+следующей\s+редакции[:\s]+[«""]?\s*(.*?)(?=\s*>?\s*[»""][\.\s]*(?:\n|$))', 'modify_paragraph')
        ]

        for pattern, change_type in patterns:
            for m in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                groups = m.groups()
                if change_type == 'modify':
                    target, old, new = groups[0].strip(), groups[1].strip(), groups[2].strip()
                else:
                    target = groups[0].strip()
                    new = groups[1].strip() if len(groups) > 1 else ""

                c_id = f"{amend_doc_id}::clause::{self._clean_id(target)}"
                self._add_node(
                    id=c_id, type="clause", clause_num=target, text=new,
                    parent_id=amend_doc_id, valid_from=valid_from, valid_to=None, source_file=filename,
                    change_status="active", change_type=change_type,
                    amends_clause=f"{base_order_id}_data::clause::{target}"
                )

    def parse_appendix_form(self, content: str, filename: str, parent_data_id: str, valid_from: str):
        """Парсит приложение с таблицей/формой (извлекает структуру HTML/Markdown)"""
        # Извлекаем заголовок и столбцы из HTML
        title_match = re.search(r'<h4\s*>(.*?)</h4\s*>', content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Приложение №1"
        
        cols = re.findall(r'<th[^>]*>(.*?)</th>', content, re.IGNORECASE | re.DOTALL)
        clean_cols = [re.sub(r'<[^>]+>', '', c).strip().replace('&nbsp;', '').replace('\n', ' ') for c in cols]
        
        self._add_node(
            id=f"{parent_data_id}::app1",
            type="form",
            heading=title,
            structure={"type": "table", "columns": clean_cols, "purpose": "Конъюнктурный анализ"},
            parent_id=parent_data_id,
            valid_from=valid_from, valid_to=None, source_file=filename
        )

    def run(self, document_set_id: str, domain: str, files_map: Dict[str, str]) -> Dict[str, Any]:
        """
        files_map: {"20200804_421.md": "content...", "20200804_421_data.md": "...", ...}
        Возвращает готовый JSON
        """

        self.doc = DocumentSet(
            id=document_set_id,
            domain=domain
        )

        # md = MarkdownIt()
        for doc_name, content in files_map.items():
            self.parse_filename(doc_name)
            self.parse_content(content)
        return {
            "metadata": self.doc.to_dict(),
            "stats": {
                "total_nodes": len(self.nodes),
                "types": {k: sum(1 for n in self.nodes if n["type"]==k) for k in set(n["type"] for n in self.nodes)}
            },
            "nodes": self.nodes
        }



        # # 1. Приказ 421
        # base_order_id = self.parse_order(files_map.get("20200804_421.md", ""), "20200804_421.md")
        # base_valid = "2020-09-28"
        # self.parse_base_methodology(files_map.get("20200804_421_data.md", ""), "20200804_421_data.md", base_order_id, base_valid)
        # self.parse_appendix_form(files_map.get("20200804_421_data_add-1.md", ""), "20200804_421_data_add-1.md", f"{base_order_id}_data", base_valid)

        # # 2. Приказ 557 (Изменение)
        # amend_order_id = self.parse_order(files_map.get("20200707_557_421.md", ""), "20200707_557_421.md")
        # amend_valid = "2022-08-31"
        # self.parse_amendments(files_map.get("20200707_557_421_add.md", ""), "20200707_557_421_add.md", base_order_id, amend_valid)

        # # Проставляем valid_to для устаревших пунктов (эвристика: все пункты до amend_valid становятся неактивны)
        # for node in self.nodes:
        #     if node.get("valid_to") is None and node.get("change_status") != "active" and node["valid_from"] < amend_valid:
        #         # Если пункт был изменён в 557, ставим ему valid_to = 2022-08-30
        #         if any(n.get("amends_clause") == node["id"] for n in self.nodes):
        #             node["valid_to"] = "2022-08-30"
        #             node["change_status"] = "superseded"

        # return {
        #     "metadata": {
        #         "document_set_id": document_set_id,
        #         "base_order": base_order_id,
        #         "latest_amendment": amend_valid,
        #         "domain": "estimating",
        #         "generated_at": datetime.datetime.now().isoformat()
        #     },
        #     "stats": {
        #         "total_nodes": len(self.nodes),
        #         "types": {k: sum(1 for n in self.nodes if n["type"]==k) for k in set(n["type"] for n in self.nodes)}
        #     },
        #     "nodes": self.nodes
        # }

# 🚀 ЗАПУСК В COLAB / ЛОКАЛЬНО
if __name__ == "__main__":
    # Пример загрузки файлов (замените пути на реальные или используйте google.colab.files.upload())
    # В Colab: from google.colab import files; uploaded = files.upload()
    # Здесь используем заглушки для демонстрации структуры. В реальности подставьте ваши .md
    
    # 📥 Замените этот блок на чтение реальных файлов:
    
    files_content = {}
    for fname in [
        "minstroy_20200804_pr_421.md", 
        "minstroy_20200804_pr_421_data.md",
        "minstroy_20220707_pr_557-421.md",
        "minstroy_20220707_pr_557-421_add.md"]:
        with open(f"{Path.cwd()}/ai/practic/2/data/md/{fname}", "r", encoding="utf-8") as f:
            files_content[fname] = f.read()
            
    # # Для демо создадим минимальные заглушки, чтобы скрипт отработал без ошибок:
    # demo_files = {
    #     "20200804_421.md": "# Свойства\nтип приказ\nномер 421/пр\nдата 04.08.2020\nОписание\nОб утверждении Методики...",
    #     "20200804_421_data.md": "I.Общие положения\n1. Методика определяет единые методы...\n2. Положения применяются...\n$$ \\text{ОТ}_{\\text{тек}} = ... $$\nII.Состав сметной документации\n1. Разрабатываются расчеты...",
    #     "20200707_557_421.md": "# Свойства\nномер 557/пр\nдата 07.07.2022\nОписание\nО внесении изменений в Методику 421...",
    #     "20200707_557_421_add.md": "Пункт 5 изложить в следующей редакции: «5. В сметной стоимости учитываются затраты...».\nДополнить пунктом 52.1 следующего содержания: 52.1. При определении...",
    #     "20200804_421_data_add-1.md": "<h4>Конъюнктурный анализ</h4><th>Код ресурса</th><th>Наименование</th>"
    # }

    builder = NormativeGraphBuilder()
    result_json = builder.run("metodika_421", "estimated", files_content)
    
    # Сохранение
    out_path = Path("data/json/metodika_421_graph.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2, default=str)
        
    print(f"✅ JSON сохранён: {out_path}")
    print(f"📊 Статистика: {result_json['stats']}")
    print(f"🔗 Пример узла (изменение):\n{json.dumps(next((n for n in result_json['nodes'] if n.get('change_type')), None), ensure_ascii=False, indent=2)}")