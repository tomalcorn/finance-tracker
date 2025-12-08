"""Integration tests for data_client module."""

from libs import backend_models, data_client


def test_get_data(
    yield_sample_user: backend_models.UserModel,
) -> None:
    """Test fetching data using sample user."""
    # Act
    data = data_client.get_data("users", "*")

    # Assert
    expected_user_model = yield_sample_user
    actual_user_model = backend_models.UserModel.model_validate(data[0])
    assert actual_user_model == expected_user_model
