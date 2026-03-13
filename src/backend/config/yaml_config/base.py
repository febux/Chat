"""
Base settings for YAML configuration class.
"""

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


class ConfigBase(BaseSettings):
    """
    Base settings for configuration class.
    """

    model_config = SettingsConfigDict(
        yaml_file="<config.yaml>",
        yaml_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        """
        Customizes the sources for loading settings from YAML file.

        :param settings_cls: The class for the settings.
        :param init_settings: The initial settings.
        :param env_settings: The settings loaded from environment variables.
        :param dotenv_settings: The settings loaded from .env file.
        :param file_secret_settings: The settings loaded from file containing secrets.
        :return: A tuple containing the YAML settings source.
        """
        return (YamlConfigSettingsSource(settings_cls),)
