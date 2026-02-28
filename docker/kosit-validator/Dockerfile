FROM eclipse-temurin:21-jre-alpine
WORKDIR /validator
ARG KOSIT_VERSION=1.5.0
ARG XRECHNUNG_CONFIG_VERSION=2024-06-20
RUN apk add --no-cache curl unzip && \
    curl -fsSL -o validator.zip \
      "https://github.com/itplr-kosit/validator/releases/download/v${KOSIT_VERSION}/validator-${KOSIT_VERSION}-distribution.zip" && \
    unzip -q validator.zip && rm validator.zip && \
    curl -fsSL -o xrechnung-config.zip \
      "https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/release-${XRECHNUNG_CONFIG_VERSION}/validator-configuration-xrechnung_3.0.2_${XRECHNUNG_CONFIG_VERSION}.zip" && \
    unzip -q xrechnung-config.zip -d xrechnung-config && rm xrechnung-config.zip && \
    apk del curl unzip
RUN addgroup -S kosit && adduser -S kosit -G kosit && chown -R kosit:kosit /validator
USER kosit
EXPOSE 8080
CMD ["java", "-jar", "validationtool-1.5.0-standalone.jar", \
     "-s", "xrechnung-config/scenarios.xml", "-D", "-H", "0.0.0.0", "-P", "8080"]
