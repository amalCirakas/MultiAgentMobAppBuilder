interface PatientProfile {
  id: string;
  firstName: string;
  lastName: string;
  dateOfBirth: Date;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
}

interface EmergencyContact {
  id: string;
  name: string;
  relationship: string;
  phoneNumber: string;
}

interface InsuranceInfo {
  id: string;
  insuranceProvider: string;
  policyNumber: string;
  effectiveDate: Date;
  expirationDate: Date;
}

interface PatientSyncIntent {
  id: string;
  patientId: string;
  syncStatus: string;
}
