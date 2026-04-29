import React from "react";
import { StyleSheet, Text, View } from "react-native";

type ModulePlaceholderScreenProps = {
  title: string;
  moduleKey: string;
};

export function ModulePlaceholderScreen({ title, moduleKey }: ModulePlaceholderScreenProps): JSX.Element {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>
        Run `MODULE={moduleKey} python3 crew.py` to generate this module screen and related files.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
    backgroundColor: "#f8fafc",
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#0f172a",
  },
  description: {
    marginTop: 10,
    textAlign: "center",
    fontSize: 14,
    color: "#334155",
  },
});
