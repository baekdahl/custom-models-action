import uuid
from collections import namedtuple

import pytest
from bson import ObjectId

from common.exceptions import InvalidModelSchema
from itertools import combinations
from schema_validator import ModelSchema


class TestSchemaValidator:
    @staticmethod
    def create_partial_model_schema(is_single=True, num_models=1):
        def _partial_model_schema(name):
            return {
                ModelSchema.MODEL_ID_KEY: str(uuid.uuid4()),
                ModelSchema.TARGET_NAME_KEY: "target_feature_col",
                ModelSchema.SETTINGS_KEY: {"name": name},
                ModelSchema.VERSION_KEY: {ModelSchema.MODEL_ENV_KEY: str(ObjectId())},
            }

        if is_single:
            model_schema = _partial_model_schema(f"single-model")
        else:
            model_schema = {ModelSchema.MULTI_MODELS_KEY: []}
            for counter in range(1, num_models + 1):
                model_name = f"model-{counter}"
                model_schema[ModelSchema.MULTI_MODELS_KEY].append(
                    {
                        ModelSchema.MODEL_ENTRY_PATH_KEY: f"./path/to/{model_name}",
                        ModelSchema.MODEL_ENTRY_META_KEY: _partial_model_schema(model_name),
                    }
                )
        return model_schema

    @pytest.fixture
    def regression_model_schema(self):
        return {
            ModelSchema.MODEL_ID_KEY: "abc123",
            ModelSchema.TARGET_TYPE_KEY: "Regression",
            ModelSchema.TARGET_NAME_KEY: "target_column",
            ModelSchema.SETTINGS_KEY: {ModelSchema.NAME_KEY: "My Awesome Model"},
            ModelSchema.VERSION_KEY: {ModelSchema.MODEL_ENV_KEY: "627785ea562155d227c6a56c"},
        }

    def test_is_single_models_schema(self):
        single_model_schema = self.create_partial_model_schema(is_single=True)
        assert ModelSchema.is_single_model_schema(single_model_schema)
        assert not ModelSchema.is_multi_models_schema(single_model_schema)

    def test_is_multi_models_schema(self):
        multi_model_schema = self.create_partial_model_schema(is_single=False, num_models=2)
        assert ModelSchema.is_multi_models_schema(multi_model_schema)
        assert not ModelSchema.is_single_model_schema(multi_model_schema)

    @pytest.mark.parametrize(
        "binary_target_type",
        [ModelSchema.TARGET_TYPE_BINARY_KEY, ModelSchema.TARGET_TYPE_UNSTRUCTURED_BINARY_KEY],
    )
    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_for_binary_model(self, binary_target_type, is_single):
        def _set_binary_keys(schema):
            schema[ModelSchema.TARGET_TYPE_KEY] = binary_target_type
            schema[ModelSchema.POSITIVE_CLASS_LABEL_KEY] = "1"
            schema[ModelSchema.NEGATIVE_CLASS_LABEL_KEY] = "0"

        self._validate_for_model_type(is_single, _set_binary_keys)

    def _validate_for_model_type(self, is_single, setup_model_keys_func):
        model_schema = self.create_partial_model_schema(is_single, num_models=1)
        with pytest.raises(InvalidModelSchema):
            # Partial schema should fail
            self._validate_schema(is_single, model_schema)

        if is_single:
            setup_model_keys_func(model_schema)
        else:
            for model_entry in model_schema[ModelSchema.MULTI_MODELS_KEY]:
                setup_model_keys_func(model_entry[ModelSchema.MODEL_ENTRY_META_KEY])

        self._validate_schema(is_single, model_schema)

    @staticmethod
    def _validate_schema(is_single, model_schema):
        if is_single:
            transformed_schema = ModelSchema().validate_and_transform_single(model_schema)

            # Validate existence of default values
            for glob_key in [
                ModelSchema.INCLUDE_GLOB_KEY,
                ModelSchema.EXCLUDE_GLOB_KEY,
            ]:
                assert isinstance(transformed_schema[ModelSchema.VERSION_KEY][glob_key], list)
        else:
            transformed_schema = ModelSchema().validate_and_transform_multi(model_schema)

            # Validate existence of default values
            for model_entry in transformed_schema[ModelSchema.MULTI_MODELS_KEY]:
                for glob_key in [
                    ModelSchema.INCLUDE_GLOB_KEY,
                    ModelSchema.EXCLUDE_GLOB_KEY,
                ]:
                    model_metadata = model_entry[ModelSchema.MODEL_ENTRY_META_KEY]
                    assert isinstance(model_metadata[ModelSchema.VERSION_KEY][glob_key], list)

    @pytest.mark.parametrize(
        "binary_target_type",
        [ModelSchema.TARGET_TYPE_BINARY_KEY, ModelSchema.TARGET_TYPE_UNSTRUCTURED_BINARY_KEY],
    )
    @pytest.mark.parametrize(
        "class_label_key",
        [ModelSchema.POSITIVE_CLASS_LABEL_KEY, ModelSchema.NEGATIVE_CLASS_LABEL_KEY, None],
    )
    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_missing_key_for_binary_model(self, binary_target_type, class_label_key, is_single):
        def _set_binary_keys(schema):
            schema[ModelSchema.TARGET_TYPE_KEY] = binary_target_type
            if class_label_key:
                schema[class_label_key] = "fake"

        with pytest.raises(InvalidModelSchema):
            self._validate_for_model_type(is_single, _set_binary_keys)

    @pytest.mark.parametrize(
        "regression_target_type",
        [
            ModelSchema.TARGET_TYPE_REGRESSION_KEY,
            ModelSchema.TARGET_TYPE_UNSTRUCTURED_REGRESSION_KEY,
        ],
    )
    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_for_regression_model(self, regression_target_type, is_single):
        def _set_regression_key(schema):
            schema[ModelSchema.TARGET_TYPE_KEY] = regression_target_type

        self._validate_for_model_type(is_single, _set_regression_key)

    @pytest.mark.parametrize(
        "multiclass_target_type",
        [
            ModelSchema.TARGET_TYPE_MULTICLASS_KEY,
            ModelSchema.TARGET_TYPE_UNSTRUCTURED_MULTICLASS_KEY,
        ],
    )
    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_for_multiclass_model(self, multiclass_target_type, is_single):
        def _set_multiclass_keys(schema):
            schema[ModelSchema.TARGET_TYPE_KEY] = multiclass_target_type
            schema[ModelSchema.CLASS_LABELS_KEY] = ["1", "2", "3"]

        self._validate_for_model_type(is_single, _set_multiclass_keys)

    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_missing_key_for_multiclass_model(self, is_single):
        def _set_multiclass_keys(schema):
            schema[ModelSchema.TARGET_TYPE_KEY] = ModelSchema.TARGET_TYPE_MULTICLASS_KEY

        with pytest.raises(InvalidModelSchema):
            self._validate_for_model_type(is_single, _set_multiclass_keys)

    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_for_unstructured_model_type(self, is_single):
        def _set_unstructured_keys(schema):
            schema[ModelSchema.TARGET_TYPE_KEY] = ModelSchema.TARGET_TYPE_UNSTRUCTURED_OTHER_KEY

        self._validate_for_model_type(is_single, _set_unstructured_keys)

    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_invalid_mutual_exclusive_keys(self, is_single):
        Key = namedtuple("Key", ["type", "name", "value"])
        mutual_exclusive_keys = {
            Key(
                type=ModelSchema.TARGET_TYPE_REGRESSION_KEY,
                name=ModelSchema.PREDICTION_THRESHOLD_KEY,
                value=0.5,
            ),
            (
                Key(
                    type=ModelSchema.TARGET_TYPE_BINARY_KEY,
                    name=ModelSchema.POSITIVE_CLASS_LABEL_KEY,
                    value="1",
                ),
                Key(
                    type=ModelSchema.TARGET_TYPE_BINARY_KEY,
                    name=ModelSchema.NEGATIVE_CLASS_LABEL_KEY,
                    value="0",
                ),
            ),
            Key(
                type=ModelSchema.TARGET_TYPE_MULTICLASS_KEY,
                name=ModelSchema.CLASS_LABELS_KEY,
                value=("a", "b", "c"),
            ),
        }

        def _set_single_model_keys(comb, schema):
            if not is_single:
                schema = schema[ModelSchema.MULTI_MODELS_KEY][0][ModelSchema.MODEL_ENTRY_META_KEY]
            for element in comb:
                if isinstance(element, Key):
                    # The 'type' is not really important here
                    schema[ModelSchema.TARGET_TYPE_KEY] = element.type
                    schema[element.name] = element.value
                else:
                    for key in element:
                        # The 'type' is not really important here
                        schema[ModelSchema.TARGET_TYPE_KEY] = key.type
                        schema[key.name] = key.value

        model_schema = self.create_partial_model_schema(is_single, num_models=1)
        comb_keys = combinations(mutual_exclusive_keys, 2)
        for comb in comb_keys:
            _set_single_model_keys(comb, model_schema)
            with pytest.raises(InvalidModelSchema):
                self._validate_schema(is_single, model_schema)

    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    @pytest.mark.parametrize(
        "mandatory_key_to_skip",
        [
            ModelSchema.MODEL_ID_KEY,
            ModelSchema.TARGET_TYPE_KEY,
            ModelSchema.TARGET_NAME_KEY,
            ModelSchema.VERSION_KEY,
            ModelSchema.SETTINGS_KEY,
            f"{ModelSchema.SETTINGS_KEY}.{ModelSchema.NAME_KEY}",
            f"{ModelSchema.VERSION_KEY}.{ModelSchema.MODEL_ENV_KEY}",
        ],
    )
    def test_missing_mandatory_keys(
        self, is_single, mandatory_key_to_skip, regression_model_schema
    ):
        key_and_sub_key = mandatory_key_to_skip.split(".")
        key = key_and_sub_key[0]
        sub_key = key_and_sub_key[1] if len(key_and_sub_key) == 2 else None
        if sub_key:
            regression_model_schema[key].pop(sub_key)
        else:
            regression_model_schema.pop(key)

        if not is_single:
            regression_model_schema = self._wrap_multi(regression_model_schema)

        with pytest.raises(InvalidModelSchema) as e:
            self._validate_schema(is_single, regression_model_schema)

        assert f"Missing key: '{sub_key if sub_key else key}'" in str(e)

    @staticmethod
    def _wrap_multi(model_schema):
        return {
            ModelSchema.MULTI_MODELS_KEY: [
                {
                    ModelSchema.MODEL_ENTRY_PATH_KEY: "./m1",
                    ModelSchema.MODEL_ENTRY_META_KEY: model_schema,
                }
            ]
        }

    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_full_model_schema(self, is_single, mock_full_binary_model_schema):
        full_model_schema = mock_full_binary_model_schema.copy()
        if not is_single:
            full_model_schema = self._wrap_multi(full_model_schema)

        self._validate_schema(is_single, full_model_schema)

    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_forbidden_extra_fields(self, is_single, regression_model_schema):
        forbidden_key = "forbidden_key"
        regression_model_schema[forbidden_key] = "Non allowed extra key"
        if not is_single:
            regression_model_schema = self._wrap_multi(regression_model_schema)
        with pytest.raises(InvalidModelSchema) as e:
            self._validate_schema(is_single, regression_model_schema)
        assert f"Wrong key '{forbidden_key}'" in str(e)

    @pytest.mark.parametrize("is_single", [True, False], ids=["single", "multi"])
    def test_dependent_stability_test_check_keys(self, is_single, regression_model_schema):
        regression_model_schema[ModelSchema.TEST_KEY] = {
            ModelSchema.TEST_DATA_KEY: "62779bef562155562769f932",
            ModelSchema.CHECKS_KEY: {
                ModelSchema.STABILITY_KEY: {
                    ModelSchema.CHECK_ENABLED_KEY: True,
                    ModelSchema.BLOCK_DEPLOYMENT_IF_FAILS_KEY: True,
                    ModelSchema.MINIMUM_PAYLOAD_SIZE_KEY: 100,
                    ModelSchema.MAXIMUM_PAYLOAD_SIZE_KEY: 50,
                }
            },
        }
        if not is_single:
            regression_model_schema = self._wrap_multi(regression_model_schema)
        with pytest.raises(InvalidModelSchema) as e:
            self._validate_schema(is_single, regression_model_schema)
        assert (
            "Stability test check minimum payload size (100) is higher than the maximum (50)"
            in str(e)
        )


class TestModelSchemaGetValue:
    def test_top_metadata(self, mock_full_binary_model_schema):
        input_metadata = mock_full_binary_model_schema
        returned_value = ModelSchema.get_value(input_metadata)
        assert returned_value == input_metadata

    def test_first_level_key(self, mock_full_binary_model_schema):
        input_metadata = mock_full_binary_model_schema
        returned_value = ModelSchema.get_value(input_metadata, ModelSchema.SETTINGS_KEY)
        assert returned_value == input_metadata[ModelSchema.SETTINGS_KEY]

    def test_second_level_key(self, mock_full_binary_model_schema):
        input_metadata = mock_full_binary_model_schema
        returned_value = ModelSchema.get_value(
            input_metadata, ModelSchema.SETTINGS_KEY, ModelSchema.DESCRIPTION_KEY
        )
        assert (
            returned_value == input_metadata[ModelSchema.SETTINGS_KEY][ModelSchema.DESCRIPTION_KEY]
        )

    def test_non_existing_key_at_first_level(self, mock_full_binary_model_schema):
        input_metadata = mock_full_binary_model_schema
        returned_value = ModelSchema.get_value(input_metadata, "non-existing-key")
        assert returned_value is None

    def test_non_existing_key_at_second_level(self, mock_full_binary_model_schema):
        input_metadata = mock_full_binary_model_schema
        returned_value = ModelSchema.get_value(
            input_metadata, ModelSchema.SETTINGS_KEY, "non-existing-key"
        )
        assert returned_value is None

    def test_unrelated_keys_at_first_level(self, mock_full_binary_model_schema):
        input_metadata = mock_full_binary_model_schema
        returned_value = ModelSchema.get_value(
            input_metadata, ModelSchema.TARGET_TYPE_KEY, ModelSchema.MODEL_ID_KEY
        )
        assert returned_value is None