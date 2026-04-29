export type PatientValidationErrors = {
  id: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
};

export function validatePatientProfile(patientProfile: PatientProfile): PatientValidationErrors {
  const errors: PatientValidationErrors = {};

  if (!patientProfile.id) {
    errors.id = 'ID is required';
  }

  if (!patientProfile.firstName) {
    errors.firstName = 'First name is required';
  }

  if (!patientProfile.lastName) {
    errors.lastName = 'Last name is required';
  }

  if (!(patientProfile.dateOfBirth instanceof Date) || isNaN(patientProfile.dateOfBirth.getTime())) {
    errors.dateOfBirth = 'Date of birth is invalid';
  }

  if (!patientProfile.address.street) {
    errors.address = {
      street: 'Street is required',
    };
  }

  if (!patientProfile.address.city) {
    errors.address = {
      ...errors.address,
      city: 'City is required',
    };
  }

  if (!patientProfile.address.state) {
    errors.address = {
      ...errors.address,
      state: 'State is required',
    };
  }

  if (!patientProfile.address.zip) {
    errors.address = {
      ...errors.address,
      zip: 'Zip is required',
    };
  }

  return errors;
}
