# FHIR Server Docker Build
# Based on https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit
# Uses ZPM package manager to install FHIR server (works with Community Edition)

ARG IMAGE=intersystemsdc/irishealth-community:latest
FROM $IMAGE as builder

# Switch to root to copy files
USER root

# Create necessary directories
WORKDIR /home/irisowner/irisdev

# Copy FHIR data set, merge config, and scripts
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./fhirdata/100Set /fhirdata/
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./merge/merge.cpf /home/irisowner/irisdev/merge.cpf
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./scripts/iris.script /home/irisowner/irisdev/iris.script
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./scripts/enablecors.script /home/irisowner/irisdev/enablecors.script
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./scripts/disable_password_expiry.script /home/irisowner/irisdev/disable_password_expiry.script
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./scripts/enable_unauthenticated_fhir.script /home/irisowner/irisdev/enable_unauthenticated_fhir.script

# Switch to IRIS user for build
USER ${ISC_PACKAGE_MGRUSER}

# Build: merge config, run setup script, disable password expiration, enable unauthenticated FHIR access, stop IRIS
RUN --mount=type=bind,src=.,dst=/home/irisowner/irisdev/src \
    iris start IRIS && \
    iris merge IRIS /home/irisowner/irisdev/merge.cpf && \
    iris session IRIS < /home/irisowner/irisdev/iris.script && \
    iris session IRIS < /home/irisowner/irisdev/enablecors.script && \
    iris session IRIS < /home/irisowner/irisdev/disable_password_expiry.script && \
    iris session IRIS < /home/irisowner/irisdev/enable_unauthenticated_fhir.script && \
    iris stop IRIS quietly

# Final image - copy the configured IRIS instance
FROM $IMAGE as final

USER root

# Copy configured database from builder
COPY --from=builder /usr/irissys /usr/irissys

# Copy FHIR data
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./fhirdata/100Set /fhirdata/

USER ${ISC_PACKAGE_MGRUSER}

# Expose ports:
# - 52773: Web interface (Management Portal, FHIR API)
# - 1972: SuperServer (database connectivity)
EXPOSE 52773 1972

# Start IRIS
ENTRYPOINT [ "/iris-main" ]
