export type PatientValidationError = {
  name?: string;
  birthdate?: string;
  address?: string;
  phoneNumber?: string;
};

export function validatePatient(patient: any): PatientValidationError | null {
  const errors: PatientValidationError = {};

  if (!patient.name) {
    errors.name = 'Name is required';
  }

  if (!patient.birthdate) {
    errors.birthdate = 'Birthdate is required';
  } else {
    const birthdate = new Date(patient.birthdate);
    if (isNaN(birthdate.getTime())) {
      errors.birthdate = 'Invalid birthdate format';
    }
  }

  if (!patient.address) {
    errors.address = 'Address is required';
  }

  if (!patient.phoneNumber) {
    errors.phoneNumber = 'Phone number is required';
  }

  return Object.keys(errors).length === 0 ? null : errors;
}