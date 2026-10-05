Personal Earprint Engine

A personal earprint engine for generating Robust Targets and Pure EarPrint IEM targets from listener-adjusted measurements.

What It Does

This project processes listener-adjusted IEM responses and measured IEM frequency responses to generate a personal target based on the listener's own earprint.

The goal is simple:

- Keep the listener's personal response characteristics
- Reduce unreliable or inconsistent features
- Generate a stable target for IEM tuning
- Allow the resulting target to be validated against measured IEM responses

Target Modes

The engine has two target modes:

Robust Target

A statistically robust personal target that keeps consistent earprint features while reducing features that are less reliable across the available measurements.

Pure EarPrint

A target that represents the listener's personal earprint with minimal robustness processing.

There is no Hybrid Graph and no third hybrid target mode.

Measurements

The engine can use IEM frequency-response measurements obtained from third-party sources, measurement databases, websites, or other published measurement resources.

Third-party measurements are used only as input data for generating personal targets.

The measurements remain the property of their respective owners.

This project does not claim ownership of third-party measurement data.

Personal Use

STRICTLY FOR PERSONAL, NON-COMMERCIAL USE.

This project is intended for personal IEM tuning and experimentation.

Users are responsible for following the terms, licenses, copyright requirements, and usage conditions of the original measurement sources.

Do not redistribute third-party measurement data unless redistribution is explicitly permitted by the original source.

Processing

The engine is designed around:

- Listener-adjusted IEM responses
- Frequency-response normalization
- Personal earprint extraction
- Robust statistical aggregation
- Median-based response analysis
- Measurement consistency analysis
- Personal target generation
- Target validation
- IEM EQ and tuning experimentation

Raw IEM frequency responses are not simply averaged to create the personal target.

Important Note

The resulting earprint is a personal audio-tuning model.

It is not:

- A clinical hearing profile
- A medical hearing test
- An anatomical HRTF measurement
- A diagnostic tool
- A replacement for professional hearing assessment

Data & Ownership

The original code and documentation in this repository belong to the project author unless otherwise stated.

Third-party measurements and other external resources remain subject to their respective owners, licenses, copyrights, and terms of use.

Third-party data should be treated as external input data and not as original project data.

Project Status

This is an ongoing personal project.

The processing pipeline, algorithms, validation methods, and implementation may change as the project develops.

License

Unless otherwise stated, the original code and documentation in this repository are intended for personal, non-commercial use only.

Third-party measurements and external resources are not covered by this repository's license and remain subject to their respective terms.

Author

Zuhir Ziyadi
