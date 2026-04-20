import { FhirResourceReader } from "./reader.js";
import { FhirResourceWriter } from "./writer.js";
import type { FetchFn, SearchParams } from "./types.js";

/**
 * FHIR R4 read client with typed accessors for all base resource types.
 *
 * @example
 * const reader = new FhirReadClient("https://fhir.example.com");
 * const pt = await reader.patient().read("123");
 */
export class FhirReadClient {
  constructor(
    protected readonly baseUrl: string,
    protected readonly fetchFn?: FetchFn,
  ) {}

  /** Get a typed resource reader for any FHIR resource type, including profile types from other generated packages. */
  forType<T extends fhir4.Resource, S extends SearchParams = SearchParams>(resourceType: string) {
    return new FhirResourceReader<T, S>(this.baseUrl, resourceType, this.fetchFn);
  }

  account() { return this.forType<fhir4.Account>("Account"); }
  activityDefinition() { return this.forType<fhir4.ActivityDefinition>("ActivityDefinition"); }
  adverseEvent() { return this.forType<fhir4.AdverseEvent>("AdverseEvent"); }
  allergyIntolerance() { return this.forType<fhir4.AllergyIntolerance>("AllergyIntolerance"); }
  appointment() { return this.forType<fhir4.Appointment>("Appointment"); }
  appointmentResponse() { return this.forType<fhir4.AppointmentResponse>("AppointmentResponse"); }
  auditEvent() { return this.forType<fhir4.AuditEvent>("AuditEvent"); }
  basic() { return this.forType<fhir4.Basic>("Basic"); }
  binary() { return this.forType<fhir4.Binary>("Binary"); }
  biologicallyDerivedProduct() { return this.forType<fhir4.BiologicallyDerivedProduct>("BiologicallyDerivedProduct"); }
  bodyStructure() { return this.forType<fhir4.BodyStructure>("BodyStructure"); }
  bundle() { return this.forType<fhir4.Bundle>("Bundle"); }
  capabilityStatement() { return this.forType<fhir4.CapabilityStatement>("CapabilityStatement"); }
  carePlan() { return this.forType<fhir4.CarePlan>("CarePlan"); }
  careTeam() { return this.forType<fhir4.CareTeam>("CareTeam"); }
  catalogEntry() { return this.forType<fhir4.CatalogEntry>("CatalogEntry"); }
  chargeItem() { return this.forType<fhir4.ChargeItem>("ChargeItem"); }
  chargeItemDefinition() { return this.forType<fhir4.ChargeItemDefinition>("ChargeItemDefinition"); }
  claim() { return this.forType<fhir4.Claim>("Claim"); }
  claimResponse() { return this.forType<fhir4.ClaimResponse>("ClaimResponse"); }
  clinicalImpression() { return this.forType<fhir4.ClinicalImpression>("ClinicalImpression"); }
  codeSystem() { return this.forType<fhir4.CodeSystem>("CodeSystem"); }
  communication() { return this.forType<fhir4.Communication>("Communication"); }
  communicationRequest() { return this.forType<fhir4.CommunicationRequest>("CommunicationRequest"); }
  compartmentDefinition() { return this.forType<fhir4.CompartmentDefinition>("CompartmentDefinition"); }
  composition() { return this.forType<fhir4.Composition>("Composition"); }
  conceptMap() { return this.forType<fhir4.ConceptMap>("ConceptMap"); }
  condition() { return this.forType<fhir4.Condition>("Condition"); }
  consent() { return this.forType<fhir4.Consent>("Consent"); }
  contract() { return this.forType<fhir4.Contract>("Contract"); }
  coverage() { return this.forType<fhir4.Coverage>("Coverage"); }
  coverageEligibilityRequest() { return this.forType<fhir4.CoverageEligibilityRequest>("CoverageEligibilityRequest"); }
  coverageEligibilityResponse() { return this.forType<fhir4.CoverageEligibilityResponse>("CoverageEligibilityResponse"); }
  detectedIssue() { return this.forType<fhir4.DetectedIssue>("DetectedIssue"); }
  device() { return this.forType<fhir4.Device>("Device"); }
  deviceDefinition() { return this.forType<fhir4.DeviceDefinition>("DeviceDefinition"); }
  deviceMetric() { return this.forType<fhir4.DeviceMetric>("DeviceMetric"); }
  deviceRequest() { return this.forType<fhir4.DeviceRequest>("DeviceRequest"); }
  deviceUseStatement() { return this.forType<fhir4.DeviceUseStatement>("DeviceUseStatement"); }
  diagnosticReport() { return this.forType<fhir4.DiagnosticReport>("DiagnosticReport"); }
  documentManifest() { return this.forType<fhir4.DocumentManifest>("DocumentManifest"); }
  documentReference() { return this.forType<fhir4.DocumentReference>("DocumentReference"); }
  effectEvidenceSynthesis() { return this.forType<fhir4.EffectEvidenceSynthesis>("EffectEvidenceSynthesis"); }
  encounter() { return this.forType<fhir4.Encounter>("Encounter"); }
  endpoint() { return this.forType<fhir4.Endpoint>("Endpoint"); }
  enrollmentRequest() { return this.forType<fhir4.EnrollmentRequest>("EnrollmentRequest"); }
  enrollmentResponse() { return this.forType<fhir4.EnrollmentResponse>("EnrollmentResponse"); }
  episodeOfCare() { return this.forType<fhir4.EpisodeOfCare>("EpisodeOfCare"); }
  eventDefinition() { return this.forType<fhir4.EventDefinition>("EventDefinition"); }
  evidence() { return this.forType<fhir4.Evidence>("Evidence"); }
  evidenceVariable() { return this.forType<fhir4.EvidenceVariable>("EvidenceVariable"); }
  exampleScenario() { return this.forType<fhir4.ExampleScenario>("ExampleScenario"); }
  explanationOfBenefit() { return this.forType<fhir4.ExplanationOfBenefit>("ExplanationOfBenefit"); }
  familyMemberHistory() { return this.forType<fhir4.FamilyMemberHistory>("FamilyMemberHistory"); }
  flag() { return this.forType<fhir4.Flag>("Flag"); }
  goal() { return this.forType<fhir4.Goal>("Goal"); }
  graphDefinition() { return this.forType<fhir4.GraphDefinition>("GraphDefinition"); }
  group() { return this.forType<fhir4.Group>("Group"); }
  guidanceResponse() { return this.forType<fhir4.GuidanceResponse>("GuidanceResponse"); }
  healthcareService() { return this.forType<fhir4.HealthcareService>("HealthcareService"); }
  imagingStudy() { return this.forType<fhir4.ImagingStudy>("ImagingStudy"); }
  immunization() { return this.forType<fhir4.Immunization>("Immunization"); }
  immunizationEvaluation() { return this.forType<fhir4.ImmunizationEvaluation>("ImmunizationEvaluation"); }
  immunizationRecommendation() { return this.forType<fhir4.ImmunizationRecommendation>("ImmunizationRecommendation"); }
  implementationGuide() { return this.forType<fhir4.ImplementationGuide>("ImplementationGuide"); }
  insurancePlan() { return this.forType<fhir4.InsurancePlan>("InsurancePlan"); }
  invoice() { return this.forType<fhir4.Invoice>("Invoice"); }
  library() { return this.forType<fhir4.Library>("Library"); }
  linkage() { return this.forType<fhir4.Linkage>("Linkage"); }
  list() { return this.forType<fhir4.List>("List"); }
  location() { return this.forType<fhir4.Location>("Location"); }
  measure() { return this.forType<fhir4.Measure>("Measure"); }
  measureReport() { return this.forType<fhir4.MeasureReport>("MeasureReport"); }
  media() { return this.forType<fhir4.Media>("Media"); }
  medication() { return this.forType<fhir4.Medication>("Medication"); }
  medicationAdministration() { return this.forType<fhir4.MedicationAdministration>("MedicationAdministration"); }
  medicationDispense() { return this.forType<fhir4.MedicationDispense>("MedicationDispense"); }
  medicationKnowledge() { return this.forType<fhir4.MedicationKnowledge>("MedicationKnowledge"); }
  medicationRequest() { return this.forType<fhir4.MedicationRequest>("MedicationRequest"); }
  medicationStatement() { return this.forType<fhir4.MedicationStatement>("MedicationStatement"); }
  medicinalProduct() { return this.forType<fhir4.MedicinalProduct>("MedicinalProduct"); }
  medicinalProductAuthorization() { return this.forType<fhir4.MedicinalProductAuthorization>("MedicinalProductAuthorization"); }
  medicinalProductContraindication() { return this.forType<fhir4.MedicinalProductContraindication>("MedicinalProductContraindication"); }
  medicinalProductIndication() { return this.forType<fhir4.MedicinalProductIndication>("MedicinalProductIndication"); }
  medicinalProductIngredient() { return this.forType<fhir4.MedicinalProductIngredient>("MedicinalProductIngredient"); }
  medicinalProductInteraction() { return this.forType<fhir4.MedicinalProductInteraction>("MedicinalProductInteraction"); }
  medicinalProductManufactured() { return this.forType<fhir4.MedicinalProductManufactured>("MedicinalProductManufactured"); }
  medicinalProductPackaged() { return this.forType<fhir4.MedicinalProductPackaged>("MedicinalProductPackaged"); }
  medicinalProductPharmaceutical() { return this.forType<fhir4.MedicinalProductPharmaceutical>("MedicinalProductPharmaceutical"); }
  medicinalProductUndesirableEffect() { return this.forType<fhir4.MedicinalProductUndesirableEffect>("MedicinalProductUndesirableEffect"); }
  messageDefinition() { return this.forType<fhir4.MessageDefinition>("MessageDefinition"); }
  messageHeader() { return this.forType<fhir4.MessageHeader>("MessageHeader"); }
  molecularSequence() { return this.forType<fhir4.MolecularSequence>("MolecularSequence"); }
  namingSystem() { return this.forType<fhir4.NamingSystem>("NamingSystem"); }
  nutritionOrder() { return this.forType<fhir4.NutritionOrder>("NutritionOrder"); }
  observation() { return this.forType<fhir4.Observation>("Observation"); }
  observationDefinition() { return this.forType<fhir4.ObservationDefinition>("ObservationDefinition"); }
  operationDefinition() { return this.forType<fhir4.OperationDefinition>("OperationDefinition"); }
  operationOutcome() { return this.forType<fhir4.OperationOutcome>("OperationOutcome"); }
  organization() { return this.forType<fhir4.Organization>("Organization"); }
  organizationAffiliation() { return this.forType<fhir4.OrganizationAffiliation>("OrganizationAffiliation"); }
  patient() { return this.forType<fhir4.Patient>("Patient"); }
  paymentNotice() { return this.forType<fhir4.PaymentNotice>("PaymentNotice"); }
  paymentReconciliation() { return this.forType<fhir4.PaymentReconciliation>("PaymentReconciliation"); }
  person() { return this.forType<fhir4.Person>("Person"); }
  planDefinition() { return this.forType<fhir4.PlanDefinition>("PlanDefinition"); }
  practitioner() { return this.forType<fhir4.Practitioner>("Practitioner"); }
  practitionerRole() { return this.forType<fhir4.PractitionerRole>("PractitionerRole"); }
  procedure() { return this.forType<fhir4.Procedure>("Procedure"); }
  provenance() { return this.forType<fhir4.Provenance>("Provenance"); }
  questionnaire() { return this.forType<fhir4.Questionnaire>("Questionnaire"); }
  questionnaireResponse() { return this.forType<fhir4.QuestionnaireResponse>("QuestionnaireResponse"); }
  relatedPerson() { return this.forType<fhir4.RelatedPerson>("RelatedPerson"); }
  requestGroup() { return this.forType<fhir4.RequestGroup>("RequestGroup"); }
  researchDefinition() { return this.forType<fhir4.ResearchDefinition>("ResearchDefinition"); }
  researchElementDefinition() { return this.forType<fhir4.ResearchElementDefinition>("ResearchElementDefinition"); }
  researchStudy() { return this.forType<fhir4.ResearchStudy>("ResearchStudy"); }
  researchSubject() { return this.forType<fhir4.ResearchSubject>("ResearchSubject"); }
  riskAssessment() { return this.forType<fhir4.RiskAssessment>("RiskAssessment"); }
  riskEvidenceSynthesis() { return this.forType<fhir4.RiskEvidenceSynthesis>("RiskEvidenceSynthesis"); }
  schedule() { return this.forType<fhir4.Schedule>("Schedule"); }
  searchParameter() { return this.forType<fhir4.SearchParameter>("SearchParameter"); }
  serviceRequest() { return this.forType<fhir4.ServiceRequest>("ServiceRequest"); }
  slot() { return this.forType<fhir4.Slot>("Slot"); }
  specimen() { return this.forType<fhir4.Specimen>("Specimen"); }
  specimenDefinition() { return this.forType<fhir4.SpecimenDefinition>("SpecimenDefinition"); }
  structureDefinition() { return this.forType<fhir4.StructureDefinition>("StructureDefinition"); }
  structureMap() { return this.forType<fhir4.StructureMap>("StructureMap"); }
  subscription() { return this.forType<fhir4.Subscription>("Subscription"); }
  substance() { return this.forType<fhir4.Substance>("Substance"); }
  substanceNucleicAcid() { return this.forType<fhir4.SubstanceNucleicAcid>("SubstanceNucleicAcid"); }
  substancePolymer() { return this.forType<fhir4.SubstancePolymer>("SubstancePolymer"); }
  substanceProtein() { return this.forType<fhir4.SubstanceProtein>("SubstanceProtein"); }
  substanceReferenceInformation() { return this.forType<fhir4.SubstanceReferenceInformation>("SubstanceReferenceInformation"); }
  substanceSourceMaterial() { return this.forType<fhir4.SubstanceSourceMaterial>("SubstanceSourceMaterial"); }
  substanceSpecification() { return this.forType<fhir4.SubstanceSpecification>("SubstanceSpecification"); }
  supplyDelivery() { return this.forType<fhir4.SupplyDelivery>("SupplyDelivery"); }
  supplyRequest() { return this.forType<fhir4.SupplyRequest>("SupplyRequest"); }
  task() { return this.forType<fhir4.Task>("Task"); }
  terminologyCapabilities() { return this.forType<fhir4.TerminologyCapabilities>("TerminologyCapabilities"); }
  testReport() { return this.forType<fhir4.TestReport>("TestReport"); }
  testScript() { return this.forType<fhir4.TestScript>("TestScript"); }
  valueSet() { return this.forType<fhir4.ValueSet>("ValueSet"); }
  verificationResult() { return this.forType<fhir4.VerificationResult>("VerificationResult"); }
  visionPrescription() { return this.forType<fhir4.VisionPrescription>("VisionPrescription"); }
}

/**
 * FHIR R4 write client with typed accessors for all base resource types.
 */
export class FhirWriteClient {
  constructor(
    protected readonly baseUrl: string,
    protected readonly fetchFn?: FetchFn,
  ) {}

  /** Get a typed resource writer for any FHIR resource type, including profile types from other generated packages. */
  forType<T extends fhir4.Resource>(resourceType: string) {
    return new FhirResourceWriter<T>(this.baseUrl, resourceType, this.fetchFn);
  }

  account() { return this.forType<fhir4.Account>("Account"); }
  activityDefinition() { return this.forType<fhir4.ActivityDefinition>("ActivityDefinition"); }
  adverseEvent() { return this.forType<fhir4.AdverseEvent>("AdverseEvent"); }
  allergyIntolerance() { return this.forType<fhir4.AllergyIntolerance>("AllergyIntolerance"); }
  appointment() { return this.forType<fhir4.Appointment>("Appointment"); }
  appointmentResponse() { return this.forType<fhir4.AppointmentResponse>("AppointmentResponse"); }
  auditEvent() { return this.forType<fhir4.AuditEvent>("AuditEvent"); }
  basic() { return this.forType<fhir4.Basic>("Basic"); }
  binary() { return this.forType<fhir4.Binary>("Binary"); }
  biologicallyDerivedProduct() { return this.forType<fhir4.BiologicallyDerivedProduct>("BiologicallyDerivedProduct"); }
  bodyStructure() { return this.forType<fhir4.BodyStructure>("BodyStructure"); }
  bundle() { return this.forType<fhir4.Bundle>("Bundle"); }
  capabilityStatement() { return this.forType<fhir4.CapabilityStatement>("CapabilityStatement"); }
  carePlan() { return this.forType<fhir4.CarePlan>("CarePlan"); }
  careTeam() { return this.forType<fhir4.CareTeam>("CareTeam"); }
  catalogEntry() { return this.forType<fhir4.CatalogEntry>("CatalogEntry"); }
  chargeItem() { return this.forType<fhir4.ChargeItem>("ChargeItem"); }
  chargeItemDefinition() { return this.forType<fhir4.ChargeItemDefinition>("ChargeItemDefinition"); }
  claim() { return this.forType<fhir4.Claim>("Claim"); }
  claimResponse() { return this.forType<fhir4.ClaimResponse>("ClaimResponse"); }
  clinicalImpression() { return this.forType<fhir4.ClinicalImpression>("ClinicalImpression"); }
  codeSystem() { return this.forType<fhir4.CodeSystem>("CodeSystem"); }
  communication() { return this.forType<fhir4.Communication>("Communication"); }
  communicationRequest() { return this.forType<fhir4.CommunicationRequest>("CommunicationRequest"); }
  compartmentDefinition() { return this.forType<fhir4.CompartmentDefinition>("CompartmentDefinition"); }
  composition() { return this.forType<fhir4.Composition>("Composition"); }
  conceptMap() { return this.forType<fhir4.ConceptMap>("ConceptMap"); }
  condition() { return this.forType<fhir4.Condition>("Condition"); }
  consent() { return this.forType<fhir4.Consent>("Consent"); }
  contract() { return this.forType<fhir4.Contract>("Contract"); }
  coverage() { return this.forType<fhir4.Coverage>("Coverage"); }
  coverageEligibilityRequest() { return this.forType<fhir4.CoverageEligibilityRequest>("CoverageEligibilityRequest"); }
  coverageEligibilityResponse() { return this.forType<fhir4.CoverageEligibilityResponse>("CoverageEligibilityResponse"); }
  detectedIssue() { return this.forType<fhir4.DetectedIssue>("DetectedIssue"); }
  device() { return this.forType<fhir4.Device>("Device"); }
  deviceDefinition() { return this.forType<fhir4.DeviceDefinition>("DeviceDefinition"); }
  deviceMetric() { return this.forType<fhir4.DeviceMetric>("DeviceMetric"); }
  deviceRequest() { return this.forType<fhir4.DeviceRequest>("DeviceRequest"); }
  deviceUseStatement() { return this.forType<fhir4.DeviceUseStatement>("DeviceUseStatement"); }
  diagnosticReport() { return this.forType<fhir4.DiagnosticReport>("DiagnosticReport"); }
  documentManifest() { return this.forType<fhir4.DocumentManifest>("DocumentManifest"); }
  documentReference() { return this.forType<fhir4.DocumentReference>("DocumentReference"); }
  effectEvidenceSynthesis() { return this.forType<fhir4.EffectEvidenceSynthesis>("EffectEvidenceSynthesis"); }
  encounter() { return this.forType<fhir4.Encounter>("Encounter"); }
  endpoint() { return this.forType<fhir4.Endpoint>("Endpoint"); }
  enrollmentRequest() { return this.forType<fhir4.EnrollmentRequest>("EnrollmentRequest"); }
  enrollmentResponse() { return this.forType<fhir4.EnrollmentResponse>("EnrollmentResponse"); }
  episodeOfCare() { return this.forType<fhir4.EpisodeOfCare>("EpisodeOfCare"); }
  eventDefinition() { return this.forType<fhir4.EventDefinition>("EventDefinition"); }
  evidence() { return this.forType<fhir4.Evidence>("Evidence"); }
  evidenceVariable() { return this.forType<fhir4.EvidenceVariable>("EvidenceVariable"); }
  exampleScenario() { return this.forType<fhir4.ExampleScenario>("ExampleScenario"); }
  explanationOfBenefit() { return this.forType<fhir4.ExplanationOfBenefit>("ExplanationOfBenefit"); }
  familyMemberHistory() { return this.forType<fhir4.FamilyMemberHistory>("FamilyMemberHistory"); }
  flag() { return this.forType<fhir4.Flag>("Flag"); }
  goal() { return this.forType<fhir4.Goal>("Goal"); }
  graphDefinition() { return this.forType<fhir4.GraphDefinition>("GraphDefinition"); }
  group() { return this.forType<fhir4.Group>("Group"); }
  guidanceResponse() { return this.forType<fhir4.GuidanceResponse>("GuidanceResponse"); }
  healthcareService() { return this.forType<fhir4.HealthcareService>("HealthcareService"); }
  imagingStudy() { return this.forType<fhir4.ImagingStudy>("ImagingStudy"); }
  immunization() { return this.forType<fhir4.Immunization>("Immunization"); }
  immunizationEvaluation() { return this.forType<fhir4.ImmunizationEvaluation>("ImmunizationEvaluation"); }
  immunizationRecommendation() { return this.forType<fhir4.ImmunizationRecommendation>("ImmunizationRecommendation"); }
  implementationGuide() { return this.forType<fhir4.ImplementationGuide>("ImplementationGuide"); }
  insurancePlan() { return this.forType<fhir4.InsurancePlan>("InsurancePlan"); }
  invoice() { return this.forType<fhir4.Invoice>("Invoice"); }
  library() { return this.forType<fhir4.Library>("Library"); }
  linkage() { return this.forType<fhir4.Linkage>("Linkage"); }
  list() { return this.forType<fhir4.List>("List"); }
  location() { return this.forType<fhir4.Location>("Location"); }
  measure() { return this.forType<fhir4.Measure>("Measure"); }
  measureReport() { return this.forType<fhir4.MeasureReport>("MeasureReport"); }
  media() { return this.forType<fhir4.Media>("Media"); }
  medication() { return this.forType<fhir4.Medication>("Medication"); }
  medicationAdministration() { return this.forType<fhir4.MedicationAdministration>("MedicationAdministration"); }
  medicationDispense() { return this.forType<fhir4.MedicationDispense>("MedicationDispense"); }
  medicationKnowledge() { return this.forType<fhir4.MedicationKnowledge>("MedicationKnowledge"); }
  medicationRequest() { return this.forType<fhir4.MedicationRequest>("MedicationRequest"); }
  medicationStatement() { return this.forType<fhir4.MedicationStatement>("MedicationStatement"); }
  medicinalProduct() { return this.forType<fhir4.MedicinalProduct>("MedicinalProduct"); }
  medicinalProductAuthorization() { return this.forType<fhir4.MedicinalProductAuthorization>("MedicinalProductAuthorization"); }
  medicinalProductContraindication() { return this.forType<fhir4.MedicinalProductContraindication>("MedicinalProductContraindication"); }
  medicinalProductIndication() { return this.forType<fhir4.MedicinalProductIndication>("MedicinalProductIndication"); }
  medicinalProductIngredient() { return this.forType<fhir4.MedicinalProductIngredient>("MedicinalProductIngredient"); }
  medicinalProductInteraction() { return this.forType<fhir4.MedicinalProductInteraction>("MedicinalProductInteraction"); }
  medicinalProductManufactured() { return this.forType<fhir4.MedicinalProductManufactured>("MedicinalProductManufactured"); }
  medicinalProductPackaged() { return this.forType<fhir4.MedicinalProductPackaged>("MedicinalProductPackaged"); }
  medicinalProductPharmaceutical() { return this.forType<fhir4.MedicinalProductPharmaceutical>("MedicinalProductPharmaceutical"); }
  medicinalProductUndesirableEffect() { return this.forType<fhir4.MedicinalProductUndesirableEffect>("MedicinalProductUndesirableEffect"); }
  messageDefinition() { return this.forType<fhir4.MessageDefinition>("MessageDefinition"); }
  messageHeader() { return this.forType<fhir4.MessageHeader>("MessageHeader"); }
  molecularSequence() { return this.forType<fhir4.MolecularSequence>("MolecularSequence"); }
  namingSystem() { return this.forType<fhir4.NamingSystem>("NamingSystem"); }
  nutritionOrder() { return this.forType<fhir4.NutritionOrder>("NutritionOrder"); }
  observation() { return this.forType<fhir4.Observation>("Observation"); }
  observationDefinition() { return this.forType<fhir4.ObservationDefinition>("ObservationDefinition"); }
  operationDefinition() { return this.forType<fhir4.OperationDefinition>("OperationDefinition"); }
  operationOutcome() { return this.forType<fhir4.OperationOutcome>("OperationOutcome"); }
  organization() { return this.forType<fhir4.Organization>("Organization"); }
  organizationAffiliation() { return this.forType<fhir4.OrganizationAffiliation>("OrganizationAffiliation"); }
  patient() { return this.forType<fhir4.Patient>("Patient"); }
  paymentNotice() { return this.forType<fhir4.PaymentNotice>("PaymentNotice"); }
  paymentReconciliation() { return this.forType<fhir4.PaymentReconciliation>("PaymentReconciliation"); }
  person() { return this.forType<fhir4.Person>("Person"); }
  planDefinition() { return this.forType<fhir4.PlanDefinition>("PlanDefinition"); }
  practitioner() { return this.forType<fhir4.Practitioner>("Practitioner"); }
  practitionerRole() { return this.forType<fhir4.PractitionerRole>("PractitionerRole"); }
  procedure() { return this.forType<fhir4.Procedure>("Procedure"); }
  provenance() { return this.forType<fhir4.Provenance>("Provenance"); }
  questionnaire() { return this.forType<fhir4.Questionnaire>("Questionnaire"); }
  questionnaireResponse() { return this.forType<fhir4.QuestionnaireResponse>("QuestionnaireResponse"); }
  relatedPerson() { return this.forType<fhir4.RelatedPerson>("RelatedPerson"); }
  requestGroup() { return this.forType<fhir4.RequestGroup>("RequestGroup"); }
  researchDefinition() { return this.forType<fhir4.ResearchDefinition>("ResearchDefinition"); }
  researchElementDefinition() { return this.forType<fhir4.ResearchElementDefinition>("ResearchElementDefinition"); }
  researchStudy() { return this.forType<fhir4.ResearchStudy>("ResearchStudy"); }
  researchSubject() { return this.forType<fhir4.ResearchSubject>("ResearchSubject"); }
  riskAssessment() { return this.forType<fhir4.RiskAssessment>("RiskAssessment"); }
  riskEvidenceSynthesis() { return this.forType<fhir4.RiskEvidenceSynthesis>("RiskEvidenceSynthesis"); }
  schedule() { return this.forType<fhir4.Schedule>("Schedule"); }
  searchParameter() { return this.forType<fhir4.SearchParameter>("SearchParameter"); }
  serviceRequest() { return this.forType<fhir4.ServiceRequest>("ServiceRequest"); }
  slot() { return this.forType<fhir4.Slot>("Slot"); }
  specimen() { return this.forType<fhir4.Specimen>("Specimen"); }
  specimenDefinition() { return this.forType<fhir4.SpecimenDefinition>("SpecimenDefinition"); }
  structureDefinition() { return this.forType<fhir4.StructureDefinition>("StructureDefinition"); }
  structureMap() { return this.forType<fhir4.StructureMap>("StructureMap"); }
  subscription() { return this.forType<fhir4.Subscription>("Subscription"); }
  substance() { return this.forType<fhir4.Substance>("Substance"); }
  substanceNucleicAcid() { return this.forType<fhir4.SubstanceNucleicAcid>("SubstanceNucleicAcid"); }
  substancePolymer() { return this.forType<fhir4.SubstancePolymer>("SubstancePolymer"); }
  substanceProtein() { return this.forType<fhir4.SubstanceProtein>("SubstanceProtein"); }
  substanceReferenceInformation() { return this.forType<fhir4.SubstanceReferenceInformation>("SubstanceReferenceInformation"); }
  substanceSourceMaterial() { return this.forType<fhir4.SubstanceSourceMaterial>("SubstanceSourceMaterial"); }
  substanceSpecification() { return this.forType<fhir4.SubstanceSpecification>("SubstanceSpecification"); }
  supplyDelivery() { return this.forType<fhir4.SupplyDelivery>("SupplyDelivery"); }
  supplyRequest() { return this.forType<fhir4.SupplyRequest>("SupplyRequest"); }
  task() { return this.forType<fhir4.Task>("Task"); }
  terminologyCapabilities() { return this.forType<fhir4.TerminologyCapabilities>("TerminologyCapabilities"); }
  testReport() { return this.forType<fhir4.TestReport>("TestReport"); }
  testScript() { return this.forType<fhir4.TestScript>("TestScript"); }
  valueSet() { return this.forType<fhir4.ValueSet>("ValueSet"); }
  verificationResult() { return this.forType<fhir4.VerificationResult>("VerificationResult"); }
  visionPrescription() { return this.forType<fhir4.VisionPrescription>("VisionPrescription"); }
}

/**
 * Main FHIR R4 Client with typed read and write accessors.
 *
 * @example
 * const client = new FhirClient("https://fhir.example.com");
 * const pt = await client.read().patient().read("123");
 * await client.write().patient().create({ resourceType: "Patient", ... });
 */
export class FhirClient {
  private readonly _read: FhirReadClient;
  private readonly _write: FhirWriteClient;

  constructor(public readonly baseUrl: string, fetchFn?: FetchFn) {
    this._read = new FhirReadClient(baseUrl, fetchFn);
    this._write = new FhirWriteClient(baseUrl, fetchFn);
  }

  read() { return this._read; }
  write() { return this._write; }
}