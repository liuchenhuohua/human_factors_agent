import csv
import math
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO

from app.domain.dataset import (
    DataQualityReport,
    FieldQualitySummary,
    QualityIssue,
    QualitySeverity,
)
from app.domain.dataset_ports import DatasetValidationError
from app.domain.preparation import DataContract, DataField, DataFieldRole, DataType


@dataclass
class _IssueAccumulator:
    severity: QualitySeverity
    message: str
    field_key: str | None
    count: int = 0
    rows: list[int] = field(default_factory=list)

    def add(self, row_number: int | None = None, count: int = 1) -> None:
        self.count += count
        if row_number is not None and len(self.rows) < 20:
            self.rows.append(row_number)


class CsvDatasetValidator:
    """Validate one CSV behind a single deterministic report interface."""

    version = "csv-contract-validator-v1"
    _boolean_values = {"true", "false", "1", "0", "yes", "no"}

    def validate(self, content: bytes, contract: DataContract) -> DataQualityReport:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise DatasetValidationError("CSV must use UTF-8 encoding") from error
        if "\x00" in text:
            raise DatasetValidationError("CSV must not contain null bytes")

        try:
            rows = list(csv.reader(StringIO(text, newline=""), strict=True))
        except csv.Error as error:
            raise DatasetValidationError(f"CSV parsing failed: {error}") from error
        if not rows or not rows[0]:
            raise DatasetValidationError("CSV header is required")

        header = [value.strip() for value in rows[0]]
        if any(not value for value in header):
            raise DatasetValidationError("CSV header contains an empty field name")

        issues: dict[tuple[str, str | None, str], _IssueAccumulator] = {}

        def add_issue(
            code: str,
            severity: QualitySeverity,
            message: str,
            field_key: str | None = None,
            row_number: int | None = None,
            count: int = 1,
        ) -> None:
            key = (code, field_key, message)
            accumulator = issues.setdefault(
                key,
                _IssueAccumulator(severity, message, field_key),
            )
            accumulator.add(row_number, count)

        duplicate_headers = sorted(
            {name for name in header if header.count(name) > 1}
        )
        if duplicate_headers:
            add_issue(
                "duplicate_columns",
                QualitySeverity.ERROR,
                f"重复字段：{', '.join(duplicate_headers)}",
                count=len(duplicate_headers),
            )

        fields = {data_field.key: data_field for data_field in contract.fields}
        missing_columns = [key for key in fields if key not in header]
        extra_columns = [key for key in header if key not in fields]
        if missing_columns:
            add_issue(
                "missing_columns",
                QualitySeverity.ERROR,
                f"缺少契约字段：{', '.join(missing_columns)}",
                count=len(missing_columns),
            )
        if extra_columns:
            add_issue(
                "extra_columns",
                QualitySeverity.ERROR,
                f"存在契约外字段：{', '.join(extra_columns)}",
                count=len(extra_columns),
            )

        missing_counts = {key: 0 for key in fields}
        invalid_counts = {key: 0 for key in fields}
        distinct_values: dict[str, set[str]] = {key: set() for key in fields}
        seen_primary_keys: set[tuple[str, ...]] = set()
        duplicate_primary_keys = 0

        data_rows = rows[1:]
        if not data_rows:
            add_issue("empty_dataset", QualitySeverity.ERROR, "CSV 不包含数据行")

        for row_index, row in enumerate(data_rows, start=2):
            if len(row) != len(header):
                add_issue(
                    "column_count_mismatch",
                    QualitySeverity.ERROR,
                    "该行字段数量与表头不一致",
                    row_number=row_index,
                )
            values = {
                key: row[index].strip() if index < len(row) else ""
                for index, key in enumerate(header)
                if key in fields
            }
            for field_key, data_field in fields.items():
                value = values.get(field_key, "")
                if self._is_missing(value, data_field):
                    missing_counts[field_key] += 1
                    if data_field.required:
                        add_issue(
                            "required_value_missing",
                            QualitySeverity.ERROR,
                            "必填字段存在缺失值",
                            field_key=field_key,
                            row_number=row_index,
                        )
                    continue
                distinct_values[field_key].add(value)
                error_message = self._validate_value(value, data_field)
                if error_message is not None:
                    invalid_counts[field_key] += 1
                    add_issue(
                        "invalid_value",
                        QualitySeverity.ERROR,
                        error_message,
                        field_key=field_key,
                        row_number=row_index,
                    )

            primary_key = tuple(values.get(key, "") for key in contract.primary_key_fields)
            primary_key_is_complete = all(
                not self._is_missing(value, fields[key])
                for key, value in zip(contract.primary_key_fields, primary_key)
            )
            if primary_key_is_complete:
                if primary_key in seen_primary_keys:
                    duplicate_primary_keys += 1
                    add_issue(
                        "duplicate_primary_key",
                        QualitySeverity.ERROR,
                        "联合主键重复",
                        row_number=row_index,
                    )
                else:
                    seen_primary_keys.add(primary_key)

        row_count = len(data_rows)
        summaries: list[FieldQualitySummary] = []
        for field_key, data_field in fields.items():
            missing_rate = missing_counts[field_key] / row_count if row_count else 0
            summaries.append(
                FieldQualitySummary(
                    field_key=field_key,
                    missing_count=missing_counts[field_key],
                    missing_rate=missing_rate,
                    invalid_count=invalid_counts[field_key],
                    distinct_count=len(distinct_values[field_key]),
                )
            )
            if missing_rate >= 0.1:
                add_issue(
                    "high_missing_rate",
                    QualitySeverity.WARNING,
                    f"字段缺失率为 {missing_rate:.1%}",
                    field_key=field_key,
                )
            if (
                row_count > 1
                and data_field.role
                in {DataFieldRole.DEPENDENT, DataFieldRole.MANIPULATION_CHECK}
                and len(distinct_values[field_key]) <= 1
            ):
                add_issue(
                    "constant_measure",
                    QualitySeverity.WARNING,
                    "测量字段没有变化，请核对采集或编码",
                    field_key=field_key,
                )

        quality_issues = [
            QualityIssue(
                code=code,
                severity=accumulator.severity,
                message=accumulator.message,
                field_key=accumulator.field_key,
                occurrence_count=accumulator.count,
                row_numbers=accumulator.rows,
            )
            for (code, _, _), accumulator in issues.items()
        ]
        error_count = sum(
            issue.occurrence_count
            for issue in quality_issues
            if issue.severity is QualitySeverity.ERROR
        )
        warning_count = sum(
            issue.occurrence_count
            for issue in quality_issues
            if issue.severity is QualitySeverity.WARNING
        )
        return DataQualityReport(
            row_count=row_count,
            column_count=len(header),
            error_count=error_count,
            warning_count=warning_count,
            duplicate_primary_key_count=duplicate_primary_keys,
            valid_for_analysis=error_count == 0 and row_count > 0,
            issues=quality_issues,
            field_summaries=summaries,
            validator_version=self.version,
        )

    @staticmethod
    def _is_missing(value: str, field: DataField) -> bool:
        return not value or value in field.missing_values

    def _validate_value(self, value: str, field: DataField) -> str | None:
        numeric_value: float | None = None
        try:
            if field.data_type is DataType.INTEGER:
                numeric_value = float(int(value))
            elif field.data_type is DataType.FLOAT:
                numeric_value = float(value)
                if not math.isfinite(numeric_value):
                    return "数值必须是有限数"
            elif field.data_type is DataType.CATEGORY:
                if value not in field.categories:
                    return f"分类值必须属于：{', '.join(field.categories)}"
            elif field.data_type is DataType.BOOLEAN:
                if value.lower() not in self._boolean_values:
                    return "布尔值必须为 true/false、yes/no 或 1/0"
            elif field.data_type is DataType.DATETIME:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, OverflowError):
            return f"值不符合 {field.data_type.value} 类型"

        if numeric_value is not None:
            if field.allowed_min is not None and numeric_value < field.allowed_min:
                return f"数值不得小于 {field.allowed_min:g}"
            if field.allowed_max is not None and numeric_value > field.allowed_max:
                return f"数值不得大于 {field.allowed_max:g}"
        return None
