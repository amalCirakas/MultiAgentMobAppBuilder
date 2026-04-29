import { Device, Element, ElementFinder, ElementArrayFinder, By, Locator } from 'detox';

describe('Patient Registration', () => {
  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('renders fields', async () => {
    const firstNameField = await element(By.id('firstName'));
    const lastNameField = await element(By.id('lastName'));
    const emailField = await element(By.id('email'));
    const phoneNumberField = await element(By.id('phoneNumber'));

    expect(await firstNameField.exists()).toBe(true);
    expect(await lastNameField.exists()).toBe(true);
    expect(await emailField.exists()).toBe(true);
    expect(await phoneNumberField.exists()).toBe(true);
  });

  it('submits valid form', async () => {
    const firstNameField = await element(By.id('firstName'));
    const lastNameField = await element(By.id('lastName'));
    const emailField = await element(By.id('email'));
    const phoneNumberField = await element(By.id('phoneNumber'));

    await firstNameField.type('John');
    await lastNameField.type('Doe');
    await emailField.type('john.doe@example.com');
    await phoneNumberField.type('1234567890');

    const submitButton = await element(By.id('submitButton'));
    await submitButton.tap();

    const successMessage = await element(By.id('successMessage'));
    expect(await successMessage.exists()).toBe(true);
  });

  it('displays validation feedback for invalid form', async () => {
    const firstNameField = await element(By.id('firstName'));
    const lastNameField = await element(By.id('lastName'));
    const emailField = await element(By.id('email'));
    const phoneNumberField = await element(By.id('phoneNumber'));

    await firstNameField.type('');
    await lastNameField.type('');
    await emailField.type('invalid-email');
    await phoneNumberField.type('');

    const submitButton = await element(By.id('submitButton'));
    await submitButton.tap();

    const errorMessage = await element(By.id('errorMessage'));
    expect(await errorMessage.exists()).toBe(true);
  });
});

export default {};
