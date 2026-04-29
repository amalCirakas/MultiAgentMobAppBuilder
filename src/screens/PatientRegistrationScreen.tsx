import React from 'react';
import { View, Text, TextInput, Button } from 'react-native';
import { PatientRegistrationForm } from './PatientRegistrationForm';
import { PatientProfileUpdateForm } from './PatientProfileUpdateForm';

interface PatientRegistrationScreenProps {
  navigation: any;
}

const PatientRegistrationScreen = ({ navigation }: PatientRegistrationScreenProps) => {
  return (
    <View>
      <Text>Registration Form</Text>
      <PatientRegistrationForm navigation={navigation} />
      <Text>Profile Update Form</Text>
      <PatientProfileUpdateForm navigation={navigation} />
      <Button title='Submit' onPress={() => navigation.navigate('Home')} />
    </View>
  );
}

export default PatientRegistrationScreen;
