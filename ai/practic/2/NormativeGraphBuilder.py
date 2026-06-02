# 📦 Скрипт: Парсинг нормативных документов в Graph-Ready JSON
import re
from pydantic import BaseModel
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum

# 🔹 1. Структура узла графа знаний
class Department(BaseModel):
    name: str = None
    fullname: str = None

    def __eq__(self, other: object) -> bool:
        # Проверяем, что сравниваемый объект тоже является экземпляром Department
        if not isinstance(other, Department):
            return False
        
        # Сравниваем только нужные поля (или все через self.model_dump())
        return self.name == other.name and self.fullname == other.fullname
    
class Signer(BaseModel):
    position: str = None
    shortname: str = None
    

class Registration(BaseModel):
    department: Department
    number: int
    registrated_at: date

class DocumentSet(BaseModel):
    id: str
    domain: str
    base_order: Optional[str] = None
    latest_amendment: Optional[str] = None
    last_updated: Optional[date] = None
    publisher: Optional[Department] = None

class NormativeNode(BaseModel):
    id: str
    type: str  # order, appendix, section, clause, amendment_order, form
    number: str | None = None
    parent_id: str | None = None
    published_at: date | None = None
    valid_from: date | None = None
    signer: Signer | None = None
    status: str | None = None
    registration: Registration | None = None
    valid_to: date | None = None
    title: str | None = None
    text: str | None = None
    change_status: str  | None = None
    change_type:    str | None = None
    amends_clause: str  | None = None
    meta: Dict[str, str] | None = None
    publisher: Department | None = None

class Result(BaseModel):
    metadata: DocumentSet
    stats: dict
    nodes: List[NormativeNode]

def NewOrderNode(id: str,
                number: str,
                parent_id: str,
                title: str,
                text: str,
                published_at: date,
                valid_from: date,
                signer: Signer,
                registration: Registration,
                publisher: Department | None = None,
                valid_to: date | None = None)-> NormativeNode:
    return NormativeNode(
        id = id,
        type="order",
        number = number,
        parent_id = parent_id,
        title = title,
        text = text,
        published_at = published_at,
        valid_from = valid_from,
        publisher = publisher,
        registration = registration,
        valid_to  = valid_to,
        signer = signer,
    )

class NormativeGraphBuilder:
    section_levels: List[str]
    level_counters: List[int] = [0]*6
    data_lines: List[str] = []
    last_number: str | None = None
    valid_froms: Dict[str, date] = {}

    def __init__(self):
        self.nodes: List[NormativeNode] = []
        self.doc: DocumentSet = {}

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
    def _parse_date(self, s: str)-> date:
        return datetime.strptime(s ,'%d.%m.%Y').date()

    def _is_base_order(self) -> bool:
        return self.number_raw.find("-") == -1
    
    def _flush_clause(self)-> bool:
        if self.data_lines:
            node = NormativeNode(
                id = self.section_levels[-1],
                parent_id=self.section_levels[-2],
                type="clause",
                text='\n'.join(self.data_lines),
                number=self.last_number,
                valid_from=self.valid_froms[self.section_levels[0]]
            )
            self.nodes.append(node)
            self.data_lines.clear()
            return True
        return False

    def addSection(self, head_level: int, text: str):
        active_counters = sum(1 for x in self.level_counters if x)
        if active_counters == head_level:
            self.section_levels.pop()
        elif active_counters > head_level:
            while active_counters > head_level and len(self.section_levels):
                self.level_counters[active_counters-1] = 0
                self.section_levels.pop()
                active_counters -= 1
            self.section_levels.pop()
        self.level_counters[head_level-1] += 1

        parts = [self.section_levels[-1], str(self.level_counters[head_level-1])]
        id = '_'.join(parts) if len(self.section_levels) == 1 else '.'.join(parts)
        node = NormativeNode(
            id=id,
            parent_id=self.section_levels[-1],
            type="section",
            text=text,
            valid_from=self.valid_froms[self.section_levels[0]]
        )                
        self.nodes.append(node)
        self.section_levels.append(id)
    
    def addClause(self, prefix:str, text:str):
        if prefix.endswith(".") :
            flushed = self._flush_clause()
            if flushed:
                mm = re.match(r'[а-яА-Я]', self.last_number)
                if mm:
                    self.section_levels.pop()
                self.section_levels.pop()
            self.last_number = prefix.removesuffix('.')
            id = '.'.join([self.section_levels[-1], self.last_number])
            self.section_levels.append(id)
        elif prefix.endswith(')'):
            flushed = self._flush_clause()
            mm = re.match(r'[а-яА-Я]', self.last_number)
            self.last_number = prefix.removesuffix(')')
            if flushed and mm:
                self.section_levels.pop()

            id = '.'.join([self.section_levels[-1], self.last_number])                    
            self.section_levels.append(id)        
        self.data_lines.append(text)

    def parse_content(self, content: str):
        if self.data_type == "":
            self.parse_order(content)
        if self.data_type == "data":
            self.parse_data(content)
        if self.data_type == "add":
            self.parse_amendments(content)
        # if data_type.startswith("add-"):
        #     node.parse_addplus(content)
    def _id(self) ->str :
        return str.join("_", [self.doc_type, self.number_raw])
    
    def _parent_id(self) -> str :
        parent_number_raw = str.join("-", self.number_raw.split("-")[1:])
        return str.join("_", [self.doc_type, parent_number_raw])
    
    def _clause_id(self, num) -> str:
        return "_".join([self._id, num])

    def parse_order(self, content: str):
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
        pid : str =None
        
        for line in lines:
            if len(line) == 0:
                continue
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
                        m = re.match(r'^(-\s\*{2})(.+)(\*{2}) +([а-яА-Я\d -\/]+$)', line)
                        if m:
                            meta[m.group(2)] = m.group(4).strip()
                    case Head.DESC:
                        desc_lines.append(line)
                    case Head.DATA:
                        data_lines.append(line)
                    case Head.Undefined:
                        print("undefined_data: ", line)

        publisher = Department(
            name=meta.get("ВедомствоСокращенно"), 
            fullname=meta.get("Ведомство")
            )
        registrar = Department(
            fullname=meta.get("ВедомствоРегистратор")
        )
        
        pub_num = meta.get("номерПубликации")
        pub_date = datetime.strptime(meta.get("датаПубликации","01.01.2000") ,'%d.%m.%Y').date()
        if self._is_base_order(): 
            if self.doc.base_order == None:
                self.doc.base_order = pub_num
                self.doc.latest_amendment = pub_num
                self.doc.publisher = publisher
        else:
            pid = self._parent_id()
            if self.doc.last_updated is None or self.doc.last_updated < pub_date:
                self.doc.latest_amendment = pub_num
                self.doc.last_updated = pub_date

        published_at = self._parse_date(meta.get("дата","01.01.2000"))
        valid_from =   self._parse_date(meta.get("вступаетВДействиеС","01.01.2000"))
        desc = "\n".join(desc_lines)
        text = "\n".join(data_lines)
        n = meta.get("номер")
        signer = Signer(position=meta.get("ПодписантДолжность"), shortname=meta.get("Подписант"))
        registration = Registration(
            department=Department(fullname=meta.get("ВедомствоРегистратор")),
            number=meta.get("номерРегистрации"),
            registrated_at=self._parse_date(meta.get("датаРегистрации","01.01.2000"))
        )
        
        node = NewOrderNode(self._id(), n, pid, desc, text, published_at, valid_from, signer, registration)
        node.publisher = None if self.doc.publisher == publisher else publisher
        if pid != None:
            node.type = "amendment_order"

        node.meta = { "city": meta.get("город") }

        self.valid_froms[self._id()] = valid_from
        self.nodes.append(node)

    def parse_data(self, content: str):
        lines = content.split('\n')
        self.data_lines=[]
        self.section_levels = [self._id()]
        self.last_number = None
        self.level_counters = [0] * 6

        for line in lines:
            m = re.match(r'^(#{1,6}|\d+\.|[а-я]\)) (.+)', line)
            if m is None:
                self.data_lines.append(line.strip())
                continue
            prefix = m.group(1)
            if prefix.startswith("#"):
                self.addSection(len(prefix), m.group(2))
            else:
                self.addClause(m.group(1).strip(), m.group(2).strip())
        self._flush_clause()

    def addAmmendent(self, text:str):
        print(text)

    def parse_amendments(self, content: str):
        lines = content.split('\n')
        
        self.data_lines=[]
        self.section_levels = [self._id()]
        self.current_pid = self._parent_id()
        self.last_number = None
        self.level_counters = [0] * 6

        isCodeBlock = False
        for line in lines:

            m = re.match(r'^(#{1,6}|\d+\.|[а-я]\)) (.+)', line)
            if m is None or isCodeBlock:
                line = line.strip()
                if line.startswith("```"):
                    isCodeBlock = not isCodeBlock
                self.data_lines.append(line)
                continue
            prefix = m.group(1)
            if prefix.startswith("#"):
                self.addSection(len(prefix), m.group(2))
            else:
                self.addClause(m.group(1).strip(), m.group(2).strip())
        self._flush_clause()

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

    # def parse_amendments(self, content: str, filename: str, base_order_id: str, valid_from: str):
    #     amend_doc_id = f"{base_order_id}_amend_{self._clean_id(valid_from)}"
    #     self._add_node(
    #         id=amend_doc_id, type="amendment_order", title="Текст изменений",
    #         parent_id=None, valid_from=valid_from, valid_to=None, source_file=filename,
    #         meta={"amends_doc": base_order_id}
    #     )

    #     # Устойчивые паттерны, игнорирующие артефакты OCR: «», "", >», ., \n
    #     patterns = [
    #         # Пункт X изложить в следующей редакции: «...»
    #         (r'Пункт\s+([^\s:;,]+)\s+изложить\s+в\s+следующей\s+редакции[:\s]+[«""]?\s*(.*?)(?=\s*>?\s*[»""][\.\s]*(?:\n|$))', 'replace'),
    #         # В пункте X слова ... заменить словами ...
    #         (r'В пункте\s+([^\s:;,]+)\s+слова\s+[«""]?(.*?)[»""]?\s+заменить\s+словами\s+[«""]?(.*?)[»""]?', 'modify'),
    #         # Дополнить пунктом X следующего содержания: ...
    #         (r'Дополнить\s+пунктом\s+([^\s:;,]+)\s+следующего\s+содержания[:\s]+(.*?)(?=\n\s*(?:Дополнить|В пункте|Пункт|Абзац|Примечание)|\Z)', 'add'),
    #         # Абзац ... пункта X изложить в следующей редакции: ...
    #         (r'Абзац\s+(.+?)\s+пункта\s+([^\s:;,]+)\s+изложить\s+в\s+следующей\s+редакции[:\s]+[«""]?\s*(.*?)(?=\s*>?\s*[»""][\.\s]*(?:\n|$))', 'modify_paragraph')
    #     ]

    #     for pattern, change_type in patterns:
    #         for m in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
    #             groups = m.groups()
    #             if change_type == 'modify':
    #                 target, old, new = groups[0].strip(), groups[1].strip(), groups[2].strip()
    #             else:
    #                 target = groups[0].strip()
    #                 new = groups[1].strip() if len(groups) > 1 else ""

    #             c_id = f"{amend_doc_id}::clause::{self._clean_id(target)}"
    #             self._add_node(
    #                 id=c_id, type="clause", clause_num=target, text=new,
    #                 parent_id=amend_doc_id, valid_from=valid_from, valid_to=None, source_file=filename,
    #                 change_status="active", change_type=change_type,
    #                 amends_clause=f"{base_order_id}_data::clause::{target}"
    #             )

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

    def run(self, document_set_id: str, domain: str, files_map: Dict[str, str]) -> Result:
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
        return Result (
            metadata=self.doc,
            stats= {
                "total_nodes": len(self.nodes),
                "types": {k: sum(1 for n in self.nodes if n.type==k) for k in set(n.type for n in self.nodes)}
            },
            nodes=self.nodes
        )

# 🚀 ЗАПУСК В COLAB / ЛОКАЛЬНО
if __name__ == "__main__":    
    files_content = {}
    for fname in [
        "minstroy_20200804_pr_421.md", 
        "minstroy_20200804_pr_421_data.md",
        "minstroy_20220707_pr_557-421.md",
        "minstroy_20220707_pr_557-421_add.md"]:
        with open(f"{Path.cwd()}/ai/practic/2/data/md/{fname}", "r", encoding="utf-8") as f:
            files_content[fname] = f.read()
            
    builder = NormativeGraphBuilder()
    result = builder.run("metodika_421", "estimated", files_content)
    # Сохранение
    out_path = Path("data/json/metodika_421_graph.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(exclude_none=True))
        
    print(f"✅ JSON сохранён: {out_path}")
    print(f"📊 Статистика: {result.stats}")
    print(f"🔗 Пример узла (изменение):\n{next((n.model_dump_json() for n in result.nodes), None)}")