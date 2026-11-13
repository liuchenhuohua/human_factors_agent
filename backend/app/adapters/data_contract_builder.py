import csv
from io import StringIO

from app.domain.experiment import ExperimentPlan, VariableRole
from app.domain.preparation import (
    DataContract,
    DataField,
    DataFieldRole,
    DataType,
    VARIABLE_ROLE_TO_DATA_ROLE,
)
from app.domain.project import GenerationMetadata


class RuleBasedDataContractBuilder:
    prompt_version = "data-contract-v1"

    def build(self, plan: ExperimentPlan, plan_hash: str) -> DataContract:
        conditions = [condition.name for condition in plan.conditions]
        fields = [
            DataField(
                key="participant_id",
                label="参与者编号",
                role=DataFieldRole.IDENTIFIER,
                data_type=DataType.STRING,
                unit=None,
                required=True,
                allowed_min=None,
                allowed_max=None,
                categories=[],
                missing_values=[],
                measurement_timing="每位参与者首次入组时生成",
                source="研究团队生成的去标识化编号",
                sensitive=True,
                validation_rules=["必须唯一", "不得使用姓名、工号或联系方式"],
            ),
            DataField(
                key="condition",
                label="实验条件",
                role=DataFieldRole.CONDITION,
                data_type=DataType.CATEGORY,
                unit=None,
                required=True,
                allowed_min=None,
                allowed_max=None,
                categories=conditions,
                missing_values=[],
                measurement_timing="每个实验条件或试次",
                source="实验分配与呈现记录",
                sensitive=False,
                validation_rules=["必须与批准实验条件完全一致"],
            ),
            DataField(
                key="trial_index",
                label="试次序号",
                role=DataFieldRole.TRIAL,
                data_type=DataType.INTEGER,
                unit=None,
                required=True,
                allowed_min=1,
                allowed_max=None,
                categories=[],
                missing_values=[],
                measurement_timing="每个试次",
                source="实验任务程序",
                sensitive=False,
                validation_rules=["同一参与者和条件内按顺序递增"],
            ),
            DataField(
                key="recorded_at",
                label="记录时间",
                role=DataFieldRole.TIMESTAMP,
                data_type=DataType.DATETIME,
                unit=None,
                required=True,
                allowed_min=None,
                allowed_max=None,
                categories=[],
                missing_values=[],
                measurement_timing="产生记录时",
                source="采集系统时钟",
                sensitive=False,
                validation_rules=["使用 ISO 8601 格式并包含时区"],
            ),
        ]
        role_counts: dict[VariableRole, int] = {}
        for variable in plan.variables:
            role_counts[variable.role] = role_counts.get(variable.role, 0) + 1
            key = f"{self._role_prefix(variable.role)}_{role_counts[variable.role]:02d}"
            is_independent = variable.role is VariableRole.INDEPENDENT
            fields.append(
                DataField(
                    key=key,
                    label=variable.name,
                    role=VARIABLE_ROLE_TO_DATA_ROLE[variable.role],
                    data_type=DataType.CATEGORY if is_independent else DataType.FLOAT,
                    unit=None,
                    required=True,
                    allowed_min=None,
                    allowed_max=None,
                    categories=conditions if is_independent else [],
                    missing_values=["NA"],
                    measurement_timing=variable.measurement_timing,
                    source=variable.measurement_method,
                    sensitive=False,
                    validation_rules=[
                        variable.operational_definition,
                        "单位、范围和异常值规则需在采集前由研究者确认",
                    ],
                )
            )
        return DataContract(
            project_id=plan.project_id,
            source_plan_id=plan.id,
            source_plan_hash=plan_hash,
            row_grain="每行代表一名参与者在一个实验条件下的一次试次或测量记录",
            primary_key_fields=["participant_id", "condition", "trial_index"],
            fields=fields,
            collection_notes=[
                "上传前必须核对变量单位、允许范围和分类编码",
                "不得在参与者编号字段中保存直接身份信息",
                "原始数据应保留只读副本，清洗操作记录到独立审计日志",
            ],
            generation=GenerationMetadata(
                generator="rule-based",
                model=None,
                prompt_version=self.prompt_version,
            ),
        )

    @staticmethod
    def _role_prefix(role: VariableRole) -> str:
        return {
            VariableRole.INDEPENDENT: "iv",
            VariableRole.DEPENDENT: "dv",
            VariableRole.CONTROL: "control",
            VariableRole.COVARIATE: "covariate",
            VariableRole.MANIPULATION_CHECK: "manipulation",
        }[role]


class CsvDataTemplateRenderer:
    def render(self, contract: DataContract) -> bytes:
        stream = StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow([field.key for field in contract.fields])
        return ("\ufeff" + stream.getvalue()).encode("utf-8")
